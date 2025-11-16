# 🧠 app/infrastructure/services/product_processing_service.py
"""
🧠 `ProductProcessingService` — оркестратор повного циклу обробки товару.

🔹 Парсить карточку (`ParserFactory`) і витягує `ProductInfo`.  
🔹 Запускає наявність та музичні рекомендації паралельно.  
🔹 Генерує контент для бота (`ProductContentService`).  
🔹 (Опційно) інтегрує size-chart пайплайн для діагностик (IMP-059).  
🔹 Повертає `ProductProcessingResult` з єдиним DTO для UI-шару.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio														# ⏳ Керуємо асинхронними викликами
import logging														# 🧾 Логування подій сервісу
from dataclasses import dataclass									# 🧱 DTO та результати
from enum import Enum, auto											# 🏷️ Коди помилок
from typing import Any, Optional, TYPE_CHECKING					# 🧰 Типізація та TYPE_CHECKING

# 🧩 Внутрішні модулі проєкту
from app.domain.ai import ProductPromptDTO							# 🧠 Промти для музики
from app.domain.products.entities import ProductInfo				# 📦 Дані про товар
from app.infrastructure.availability.availability_processing_service import (
    AvailabilityProcessingService,									# ✅ Звіт про наявність
)
from app.infrastructure.content.product_content_service import (
    ProductContentDTO,												# 📝 Зібраний контент
    ProductContentService,											# 🧵 Сервіс генерації контенту
)
from app.infrastructure.music.music_recommendation import MusicRecommendation	# 🎵 Добір музики
from app.infrastructure.parsers.parser_factory import ParserFactory			# 🧩 Фабрика парсерів
from app.shared.utils.logger import LOG_NAME									# 🏷️ Базове ім'я логера
from app.shared.utils.url_parser_service import UrlParserService				# 🌍 Метадані URL

# 🆕 (IMP-059) Опційна інтеграція size chart
if TYPE_CHECKING:															# 🧠 Для типізації в IDE
    from app.infrastructure.size_chart.size_chart_service import SizeChartService	# type: ignore
else:																		# 🧮 У рантаймі модуль може бути відсутнім
    try:
        from app.infrastructure.size_chart.size_chart_service import SizeChartService  # type: ignore
    except Exception:														# 🪃 Ігноруємо, якщо модуль не підключено
        SizeChartService = None  # type: ignore[misc]

logger = logging.getLogger(LOG_NAME)										# 🧾 Створюємо іменований логер


# ================================
# 🩺 DTO ДІАГНОСТИК (IMP-059)
# ================================
@dataclass(frozen=True)
class Diagnostics:
    """🩺 Додаткові метрики size-chart/зображень для UI."""

    images_count: int														# 🖼️ Скільки зображень у фінальному контенті
    has_size_chart: bool													# 📏 Чи вдалося згенерувати size chart
    ocr_status: str															# 🔤 Статус OCR ("ok" | "not_found" | "failed" | "not_run")


# ================================
# 📦 DTO УСПІШНОЇ ОБРОБКИ
# ================================
@dataclass(frozen=True)
class ProcessedProductData:
    """📦 Уніфікований результат, який споживає бот/UI."""

    url: str																# 🔗 Початковий URL товару
    page_source: str														# 🧾 HTML джерело (для дебагу)
    region_display: str														# 🌍 Людяний регіон/локаль
    content: ProductContentDTO												# 📝 Згенерований контент
    music_text: str															# 🎵 Результат музичної рекомендації
    diagnostics: Diagnostics												# 🩺 Діагностики size-chart/зображень


# ================================
# ❌ ПОМИЛКИ ТА РЕЗУЛЬТАТ
# ================================
class ProcessingErrorCode(Enum):
    """🚨 Перелік кодів помилок для ProductProcessingResult."""

    InvalidInput = auto()													# 🔗 Некоректний URL
    ParsingFailed = auto()													# 🧨 Парсер не впорався
    ContentBuildFailed = auto()												# 🧵 Контент не зібрано
    UnexpectedError = auto()												# ❓ Резерв для несподіваних збоїв


@dataclass(frozen=True)
class ProductProcessingResult:
    """📬 Обгортка для успішного/невдалого результату."""

    ok: bool																# ✅ Прапорець успіху
    data: Optional[ProcessedProductData] = None								# 📦 DTO при успіху
    error_code: Optional[ProcessingErrorCode] = None						# 🚨 Код помилки
    error_message: Optional[str] = None										# 🧾 Опис помилки
    _cause: Optional[BaseException] = None									# 🐞 Внутрішня причина (для логів)

    @staticmethod
    def success(data: ProcessedProductData) -> "ProductProcessingResult":
        """✅ Успішний результат."""

        return ProductProcessingResult(ok=True, data=data)					# 📬 Повертаємо DTO

    @staticmethod
    def fail(
        code: ProcessingErrorCode,
        message: str,
        *,
        cause: Optional[BaseException] = None,
    ) -> "ProductProcessingResult":
        """❌ Невдалий результат з кодом помилки."""

        return ProductProcessingResult(										# 📬 Формуємо опис помилки
            ok=False,
            error_code=code,
            error_message=message,
            _cause=cause,
        )


# ================================
# 🏛️ ОСНОВНИЙ СЕРВІС ОРКЕСТРАЦІЇ
# ================================
class ProductProcessingService:
    """
    🏛️ Оркеструє повний цикл обробки товару:
        1) парсинг картки,
        2) отримання звіту про наявність,
        3) генерація контенту,
        4) підбір музики,
        5) опційний size-chart OCR з діагностиками (IMP-059).
    """

    def __init__(
        self,
        parser_factory: ParserFactory,
        availability_processing_service: AvailabilityProcessingService,
        content_service: ProductContentService,
        music_recommendation: MusicRecommendation,
        url_parser_service: UrlParserService,
        *,
        size_chart_service: Optional["SizeChartService"] = None,
    ) -> None:
        self.parser_factory = parser_factory								# 🧩 Постачальник парсерів
        self.availability_processing_service = availability_processing_service	# ✅ Сервіс наявності
        self.content_service = content_service								# 📝 Будівник контенту
        self.music_recommendation = music_recommendation					# 🎵 Музичні рекомендації
        self.url_parser_service = url_parser_service						# 🌍 Метадані URL
        self.size_chart_service = size_chart_service						# 📏 Опційний size-chart сервіс
        logger.debug(
            "🧠 ProductProcessingService ready (size_chart_enabled=%s)",
            self.size_chart_service is not None,
        )

    @staticmethod
    def _extract_sku_from_url(url: str) -> Optional[str]:
        """Повертає SKU з YoungLA URL (`/products/<sku>`), якщо його можна виокремити."""

        if not isinstance(url, str):
            return None

        raw = url.strip()
        if not raw:
            return None

        candidate = raw
        if "://" in raw:
            path_part = raw.split("://", 1)[1]
            candidate = path_part.rsplit("/", 1)[-1]

        candidate = candidate.split("?", 1)[0].split("#", 1)[0].strip()

        return candidate or None

    # ================================
    # 🔗 ПУБЛІЧНЕ API
    # ================================
    async def process_url(self, url: str) -> ProductProcessingResult:
        """🔗 Головний сценарій: URL → ProductProcessingResult."""

        logger.info("⚙️ Старт обробки URL: %s", url)						# 🧾 Фіксуємо старт пайплайна

        # 0) Валідація входу
        if not isinstance(url, str) or not url.strip():						# 🚫 Некоректний URL
            message = "Порожній або некоректний URL."						# 🧾 Опис проблеми
            logger.error("❌ %s", message)									# 🧾 Лог помилки
            return ProductProcessingResult.fail(							# 📬 Формуємо помилку
                ProcessingErrorCode.InvalidInput,
                message,
            )

        product_sku = self._extract_sku_from_url(url)					# 🔖 Прагнемо витягнути артикул з URL

        # 1) Парсимо картку
        try:
            parser = self.parser_factory.create_product_parser(url)			# 🧩 Підбираємо парсер
            logger.debug("🧩 Використано парсер %s для %s.", parser.__class__.__name__, url)
            product_info = await parser.get_product_info()					# 🧾 Тягнемо дані товару
            logger.info("📦 Отримано дані товару: title='%s'", (product_info.title or "").strip()[:80])
        except asyncio.CancelledError:										# 🛑 Скасування корутини
            logger.info("🛑 Відміна process_url для %s", url)
            raise
        except Exception as exc:												# 🔥 Інші помилки парсингу
            logger.exception("🔥 Непередбачена помилка парсингу: %s", url)
            return ProductProcessingResult.fail(
                ProcessingErrorCode.ParsingFailed,
                "Не вдалося обробити сторінку товару.",
                cause=exc,
            )
        if not isinstance(product_info, ProductInfo) or not (product_info.title or "").strip():
            logger.error("❌ Не вдалося отримати базову інформацію про товар: %s", url)
            return ProductProcessingResult.fail(
                ProcessingErrorCode.ParsingFailed,
                "Не вдалося отримати дані про товар.",
            )

        # 2) Регіон/slug (UI-метадані)
        try:
            region_display = self.url_parser_service.get_region_label(url)	# 🌍 Людяний регіон для UI
        except Exception:													# 🛟 Fallback, якщо сервіс недоступний
            logger.debug("⚠️ UrlParser недоступний — fallback на 'N/A'", exc_info=True)
            region_display = "N/A"											# 🌍 Значення за замовчуванням
        else:
            logger.debug("🌍 Region/локаль: %s", region_display)

        # 3) Паралельно: availability + music
        availability_task = self.availability_processing_service.process(url)	# 🔄 Корутинa для наявності

        product_dto = ProductPromptDTO(										# 🧠 DTO для музичної рекомендації
            title=product_info.title or "",
            description=product_info.description or "",
            image_url=product_info.image_url or "",
        )
        music_task = self.music_recommendation.recommend(product_dto)		# 🎵 Корутинa для музики

        availability_data: Any = None										# 📦 Результат наявності
        music_result: Any = None											# 🎵 Результат музики
        try:
            availability_data, music_result = await asyncio.gather(			# 🤝 Запускаємо паралельно
                availability_task,
                music_task,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:												# 🔥 Нестримні помилки — лог і продовжуємо
            logger.exception("🔥 Помилка під час паралельних запитів (наявність/музика): %s", exc)
        else:
            logger.debug(
                "✅ Паралельні таски завершені: availability=%s music=%s",
                type(availability_data).__name__ if availability_data else None,
                type(music_result).__name__ if music_result else None,
            )

        # 4) Текст кольори/розміри (із availability)
        colors_text = (														# 🎨 Формуємо текст про наявність
            getattr(getattr(availability_data, "reports", None), "public_report", None)
            or "Не вдалося отримати дані про наявність."
        )

        # 5) Контент для картки
        try:
            content_data = await self.content_service.build_product_content(	# 📝 Генеруємо опис/хештеги
                product_info,
                url=url,
                colors_text=colors_text,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:												# 🔥 Контент не зібрано
            logger.exception("❌ Не вдалося зібрати контент для товару: %s", exc)
            return ProductProcessingResult.fail(
                ProcessingErrorCode.ContentBuildFailed,
                "Не вдалося згенерувати контент для товару.",
                cause=exc,
            )
        logger.info(
            "📝 Контент зібрано: images=%d hashtags=%d",
            len(content_data.images or []),
            len(getattr(content_data, "hashtags", []) or []),
        )

        # 6) 🆕 Size-chart OCR (best-effort) → diagnostics.has_size_chart/ocr_status
        sc_has_chart = False												# 📏 Чи з'явився size chart
        sc_status = "not_run"												# 🧬 Початковий статус OCR
        page_source = getattr(parser, "page_source", "") or ""				# 🧾 HTML для diagnostics

        if self.size_chart_service is not None and page_source:		# ✅ Сервіс доступний і маємо HTML
            try:
                chart_paths = await self.size_chart_service.process_all_size_charts(
                    page_source,
                    product_sku=product_sku,
                )  # 📏 Запускаємо пайплайн з урахуванням SKU
                sc_has_chart = bool(chart_paths)							# 📌 Виставляємо прапорець
                sc_status = "ok" if sc_has_chart else "not_found"			# 🧾 Статус OCR
                logger.debug("📏 SizeChart результат: %s (%s)", sc_status, chart_paths)
            except asyncio.CancelledError:
                raise
            except Exception as exc:											# 🔥 Size-chart деградував — лог і рухаємось
                logger.warning("⚠️ SizeChart пайплайн впав: %s", exc, exc_info=True)
                sc_has_chart = False
                sc_status = "failed"

        # 7) 🆕 Підрахунок зображень у фінальному контенті
        images_count = len(content_data.images or [])						# 🖼️ Кількість картинок
        logger.debug("🖼️ У фінальному контенті %d зображень.", images_count)

        # 8) Збір результату
        result_data = ProcessedProductData(									# 📦 Формуємо фінальне DTO
            url=url,
            page_source=page_source,
            region_display=region_display,
            content=content_data,
            music_text=getattr(music_result, "raw_text", "") or "",			# 🎵 safe fallback
            diagnostics=Diagnostics(
                images_count=images_count,
                has_size_chart=sc_has_chart,
                ocr_status=sc_status,
            ),
        )
        return ProductProcessingResult.success(result_data)					# ✅ Повертаємо успіх
