# 📦 app/infrastructure/availability/availability_manager.py
"""
📦 Керує перевіркою наявності товарів у кожному регіоні.

🔹 Інкапсулює роботу з доменним сервісом `IAvailabilityService` та побудовою звітів.
🔹 Веде кешування, Prometheus-метрики та детальне логування сценарію.
🔹 Нормалізує сирі дані парсерів у `AvailabilityStatus` для відображення у боті.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (зовнішніх залежностей немає)										# 🚫 Усе усередині проєкту

# 🔠 Системні імпорти
import asyncio														# ⏱️ Паралельні виклики парсерів
import logging														# 🧾 Логування кроків сценарію
from typing import Any, Dict, List, Mapping, Optional				# 📐 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService				# ⚙️ Конфігураційні значення
from app.domain.availability.interfaces import (					# 🧠 Доменно-орієнтований сервіс
    IAvailabilityService,
    RegionStock,
)
from app.domain.availability.status import AvailabilityStatus		# 📊 Уніфікований статус наявності
from app.infrastructure.availability.cache_service import AvailabilityCacheService  # 💾 Кеш результатів
from app.infrastructure.availability.dto import AvailabilityReports	# 📦 DTO фінального звіту
from app.infrastructure.availability.metrics import (				# 📈 Prometheus-лічильники
    AV_CACHE_HITS,
    AV_CACHE_MISSES,
    AV_REPORT_LATENCY,
)
from app.infrastructure.availability.report_builder import AvailabilityReportBuilder  # 📝 Формування текстів
from app.infrastructure.parsers.parser_factory import ParserFactory	# 🧩 Створення парсерів товарів
from app.shared.utils.logger import LOG_NAME						# 🏷️ Спільний неймспейс логів
from app.shared.utils.url_parser_service import UrlParserService	# 🔍 Нормалізація URL під регіони


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)								# 🧾 Ініціалізуємо іменований логер


# ================================
# 🔧 ДОПОМІЖНІ АДАПТЕРИ
# ================================
def _to_status(value: Any) -> AvailabilityStatus:
    """🔄 Приводить довільне значення до `AvailabilityStatus`."""
    if isinstance(value, AvailabilityStatus):						# 🧾 Вже готовий статус
        return value													# ↩️ Повертаємо як є
    if value is True:													# ✅ Є на складі
        return AvailabilityStatus.YES									# 📦 Фіксуємо YES
    if value is False:													# ❌ Немає на складі
        return AvailabilityStatus.NO									# 🚫 Фіксуємо NO
    return AvailabilityStatus.UNKNOWN									# ❔ Будь-яке інше значення → UNKNOWN


def _adapt_stock_data(
    raw: Optional[Mapping[str, Mapping[str, Any]]],
) -> Dict[str, Dict[str, AvailabilityStatus]]:
    """
    ♻️ Конвертує вкладені словники `color -> size -> bool` у `AvailabilityStatus`.

    Порожні кольори/розміри відкидаються, щоби уникнути «битих» записів у звіті.
    """
    adapted: Dict[str, Dict[str, AvailabilityStatus]] = {}			# 📦 Фінальна структура
    if not raw:														# 🚫 Немає даних від парсера
        logger.debug("⚠️ availability.adapt_stock_empty")			# 🪵 Фіксуємо порожнє джерело
        return adapted												# ↩️ Повертаємо порожній словник

    for color, sizes in raw.items():									# 🎨 Проходимо всі кольори
        if not color or not sizes:										# 🚫 Пропускаємо некоректні ключі
            continue
        color_key = str(color).strip()								# 🧹 Нормалізуємо назву кольору
        if not color_key:												# 🚫 Після нормалізації може зникнути
            continue
        dst = adapted.setdefault(color_key, {})						# ♻️ Ініціалізуємо карту розмірів
        for size, flag in sizes.items():								# 📏 Проходимо всі розміри
            size_key = str(size).strip()								# 🧹 Нормалізуємо назву розміру
            if not size_key:											# 🚫 Порожні ключі відкидаємо
                continue
            dst[size_key] = _to_status(flag)							# 🔄 Перетворюємо значення у статус

    logger.debug(
        "✅ availability.stock_adapted",
        extra={"colors": len(adapted)},								# 🎨 Скільки кольорів розібрано
    )																	# 🪵 Діагностика адаптації
    return adapted													# 📦 Повертаємо уніфіковану карту


# ================================
# 🧠 МЕНЕДЖЕР НАЯВНОСТІ
# ================================
class AvailabilityManager:
    """🧠 Оркеструє збір даних по регіонах, кешування та побудову звітів."""

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        availability_service: IAvailabilityService,
        parser_factory: ParserFactory,
        cache_service: AvailabilityCacheService,
        report_builder: AvailabilityReportBuilder,
        config_service: ConfigService,
        url_parser_service: UrlParserService,
    ) -> None:
        self._availability_service = availability_service				# 🧠 Доменний агрегатор
        self._parser_factory = parser_factory							# 🧩 Вибір потрібного парсера
        self._cache = cache_service									# 💾 Тримання готових звітів
        self._report_builder = report_builder							# 📝 Формування людинозрозумілих звітів
        self._config = config_service									# ⚙️ Доступ до конфігів
        self._url_parser = url_parser_service							# 🔍 Конструювання URL під регіони

        self._cache_ttl_sec: int = int(								# ⏳ TTL кешу у секундах
            self._config.get("availability.cache_ttl_sec", 300, int) or 300
        )

        regions_cfg = self._config.get("regions", {}, dict) or {}		# 🌍 Сирий блок конфіга по регіонах
        self._region_labels: Dict[str, str] = dict(					# 🏷️ Лейбли для легенди звіту
            regions_cfg.get("labels", {}) or {}
        )
        self._regions: Dict[str, Dict[str, Any]] = {
            code: data													# 🌐 Власне регіони
            for code, data in regions_cfg.items()
            if code != "labels" and isinstance(data, dict)
        }																# 🧭 Відсіюємо службові ключі

        logger.info(
            "🧠 availability.manager_init",
            extra={
                "cache_ttl_sec": self._cache_ttl_sec,					# ⏳ TTL кешу
                "regions": list(self._regions.keys()),					# 🌍 Код регіонів
            },
        )																# 🪵 Фіксуємо параметри ініціалізації

    # ================================
    # 📣 ПУБЛІЧНИЙ МЕТОД
    # ================================
    async def get_availability_report(self, product_path: str) -> AvailabilityReports:
        """
        📣 Формує повний звіт про наявність товару.

        Повертає кеш або запускає збір даних, синхронізуючи метрики.
        """
        logger.info(
            "🧾 availability.report_start",
            extra={"product_path": product_path},						# 🧵 Трекінг товару
        )																# 🪵 Старт сценарію

        cached_report = self._cache.get(product_path, self._cache_ttl_sec)  # 💾 Пробуємо читати кеш
        if isinstance(cached_report, AvailabilityReports):				# ✅ Вдалось знайти у кеші
            AV_CACHE_HITS.inc()											# 📈 Фіксуємо хіт
            logger.info(
                "🟢 availability.cache_hit",
                extra={"product_path": product_path},
            )															# 🪵 Репорт для моніторингу
            return cached_report										# ↩️ Віддаємо кешовану версію

        AV_CACHE_MISSES.inc()											# 📉 Промах по кешу
        logger.info(
            "🟡 availability.cache_miss",
            extra={"product_path": product_path},
        )																# 🪵 Попереджаємо про холодний запит

        with AV_REPORT_LATENCY.time():									# ⏱️ Вимірюємо латентність збору
            regional_stocks = await self._fetch_all_regions(product_path)	# 🌍 Тягнемо запаси з усіх регіонів
            domain_report = self._availability_service.create_report(regional_stocks)  # 🧠 Агрегуємо доменні дані
            final_reports = self._report_builder.build(				# 📝 Формуємо DTO для UI
                region_results=regional_stocks,
                report_dto=domain_report,
            )
            self._cache.set(product_path, final_reports)				# 💾 Кешуємо гарячий результат
            logger.info(
                "✅ availability.report_built",
                extra={"product_path": product_path},
            )															# 🪵 Репортуємо завершення
            return final_reports										# 📦 Повертаємо свіжий звіт

    # ================================
    # 🔒 ВНУТРІШНІ МЕТОДИ
    # ================================
    async def _fetch_all_regions(self, product_path: str) -> List[RegionStock]:
        """🔄 Паралельно будує `RegionStock` для кожного регіону."""
        region_codes = list(self._regions.keys())						# 🌍 Знімаємо перелік регіонів
        logger.debug(
            "🧮 availability.fetch_all_regions.start",
            extra={"product_path": product_path, "regions": region_codes},
        )																# 🪵 Протоколюємо завдання
        tasks = [
            self._fetch_region_data(code, product_path)
            for code in region_codes
        ]																# 👥 Готуємо задачі на кожен регіон
        results = await asyncio.gather(*tasks)							# 🤝 Чекаємо завершення всіх задач
        logger.debug(
            "📦 availability.fetch_all_regions.done",
            extra={"product_path": product_path},
        )																# 🪵 Підтверджуємо завершення
        return results													# 📦 Повертаємо список запасів

    async def _fetch_region_data(self, region_code: str, product_path: str) -> RegionStock:
        """📥 Завантажує дані про товар для конкретного регіону."""
        logger.debug(
            "🌐 availability.fetch_region.start",
            extra={"product_path": product_path, "region": region_code},
        )																# 🪵 Старт регіонального запиту

        url = self._url_parser.build_product_url(region_code, product_path)	# 🔗 Будуємо регіональний URL
        if not url:														# 🚫 Вийшла некоректна URL
            logger.error(
                "❌ availability.region_url_failed",
                extra={"product_path": product_path, "region": region_code},
            )															# 🪵 Фіксуємо проблему
            empty_stock = RegionStock(region_code=region_code, stock_data={})  # 📭 Порожній результат
            return empty_stock											# ↩️ Повертаємо UNKNOWN-регіон

        try:
            parser = self._parser_factory.create_product_parser(		# 🧩 Створюємо регіональний парсер
                url,
                enable_progress=False,
            )
            product_info = await parser.get_product_info()				# 📦 Тягнемо дані товару

            invalid_title = getattr(product_info, "title", None) == "Помилка"  # ⚠️ Перевіряємо маркер помилки
            if not product_info or invalid_title:						# 🚫 Немає валідних даних
                logger.warning(
                    "⚠️ availability.region_product_invalid",
                    extra={"product_path": product_path, "region": region_code},
                )														# 🪵 Попереджаємо про порожню відповідь
                return RegionStock(region_code=region_code, stock_data={})  # 📭 Повертаємо UNKNOWN

            stock_data_raw = getattr(product_info, "stock_data", None)	# 📂 Беремо карту наявності
            status_stock = _adapt_stock_data(stock_data_raw)			# 🔄 Конвертуємо у статуси
            region_stock = RegionStock(region_code=region_code, stock_data=status_stock)  # 📦 Укладаємо у DTO
            logger.debug(
                "🟢 availability.region_fetch_success",
                extra={
                    "product_path": product_path,
                    "region": region_code,
                    "colors": len(status_stock),
                },
            )															# 🪵 Підтверджуємо успіх
            return region_stock										# 📦 Віддаємо результат

        except asyncio.CancelledError:
            logger.info(
                "🛑 availability.region_fetch_cancelled",
                extra={"product_path": product_path, "region": region_code},
            )															# 🪵 Протоколюємо скасування
            raise														# 🔁 Не ковтаємо cancellation
        except Exception as exc:										# noqa: BLE001 # 🚨 Будь-який інший збій
            logger.exception(
                "🔥 availability.region_fetch_failed",
                extra={
                    "product_path": product_path,
                    "region": region_code,
                    "error": str(exc),
                },
            )															# 🪵 Показуємо стектрейс
            return RegionStock(region_code=region_code, stock_data={})  # 📭 Повертаємо UNKNOWN


__all__ = ["AvailabilityManager"]										# 📦 Експортуємо публічний клас
