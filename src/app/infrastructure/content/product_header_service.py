# 🧠 app/infrastructure/content/product_header_service.py
"""
🧠 Формує легкі «заголовки» товарів (title + головне фото + canonical URL) без повного пайплайна.

🔹 `ProductHeaderService` використовує `ParserFactory` та `HtmlDataExtractor`, щоб швидко витягнути мінімальний набір даних.  
🔹 Використовується для превʼю/каруселей, де не потрібна повна агрегація контенту.  
🔹 Має best-effort поведение: повертає заглушку, якщо дані недоступні, але логує контекст.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування життєвого циклу
from dataclasses import dataclass                                    # 📦 DTO заголовка
from typing import Optional, TYPE_CHECKING                           # 📐 Типізація

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.parsers.html_data_extractor import HtmlDataExtractor  # 🧾 Витяг HTML
from app.infrastructure.parsers.parser_factory import ParserFactory            # 🏗️ Фабрика парсерів
from app.shared.utils.logger import LOG_NAME                                   # 🏷️ Імʼя логера
from app.shared.utils.url_parser_service import UrlParserService              # 🔗 Побудова URL

if TYPE_CHECKING:                                                             # 🧠 Підказки лише для аналізу
    from app.infrastructure.parsers.base_parser import BaseParser             # type: ignore

logger = logging.getLogger(LOG_NAME)                                          # 🧾 Модульний логер


# ================================
# 📦 DTO-ЗАГОЛОВОК
# ================================
@dataclass(frozen=True)
class ProductHeaderDTO:
    """📦 Мінімальний набір даних: назва, головний кадр, канонічний URL."""

    title: str                                                              # 🏷️ Назва (у верхньому регістрі)
    image_url: Optional[str]                                                # 🖼️ URL головного зображення
    product_url: str                                                        # 🔗 Канонічний URL товару


__all__ = ["ProductHeaderService", "ProductHeaderDTO"]


# ================================
# 🏛️ СЕРВІС ПОБУДОВИ ЗАГОЛОВКІВ
# ================================
class ProductHeaderService:
    """🏛️ Стандартизовано витягує мінімальний набір даних товару."""

    def __init__(
        self,
        parser_factory: ParserFactory,
        url_parser_service: UrlParserService,
    ) -> None:
        self._parser_factory = parser_factory                                # 🏗️ Фабрика парсерів
        self._url_parser = url_parser_service                                # 🔗 Сервіс побудови URL
        logger.debug("⚙️ ProductHeaderService init (parser_factory=%s)", parser_factory)

    async def create_header(self, product_path: str, region: str = "us") -> Optional[ProductHeaderDTO]:
        """🔄 Формує DTO із title/image/url або повертає None у разі фатальної помилки."""
        url = self._url_parser.build_product_url(region, product_path)       # 🌐 Будуємо канонічний URL
        if not url:
            logger.error("❌ Не вдалося побудувати URL (region=%s, path=%s)", region, product_path)
            return None

        logger.info("🏷️ Створення заголовка для: %s", url)

        try:
            parser = self._parser_factory.create_product_parser(             # 🧵 Ініціалізуємо парсер
                url,
                enable_progress=False,
            )

            await parser._fetch_and_prepare_soup()  # type: ignore[attr-defined]  # ⚠️ Використовуємо приватний API (тимчасово)
            soup = getattr(parser, "_page_soup", None)                       # type: ignore[attr-defined]
            if soup is None:
                raise ConnectionError("Не вдалося завантажити HTML для заголовка.")

            extractor = HtmlDataExtractor(soup)                               # 🧾 Легковаговий екстрактор
            title = extractor.extract_title()                       # 🏷️ Витягуємо назву зі сторінки
            image_url = extractor.extract_main_image()               # 🖼️ Беремо головний кадр
            logger.debug("🔍 Header extractor: title=%r image=%r", title, image_url)

            if not title or "помилка" in title.lower() or "без назви" in title.lower():
                logger.warning("⚠️ Невалідний title для %s: %r", url, title)
                return ProductHeaderDTO(title="🔗 ТОВАР", image_url=None, product_url=url)

            normalized_title = title.upper()                         # 🔠 Уніфікуємо регістр для UI
            return ProductHeaderDTO(title=normalized_title, image_url=image_url, product_url=url)

        except Exception as exc:  # noqa: BLE001
            logger.exception("🔥 Помилка при створенні заголовка (%s): %s", product_path, exc)
            return ProductHeaderDTO(title="🔗 ТОВАР", image_url=None, product_url=url)  # 🛡️ Повертаємо заглушку
