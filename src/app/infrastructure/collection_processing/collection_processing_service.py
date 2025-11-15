# 🧳 app/infrastructure/collection_processing/collection_processing_service.py
"""
🧳 Сервіс витягує посилання на товари зі сторінки колекції.

🔹 Нормалізує та валідовує URL перед роботою.  
🔹 Створює провайдер через `ParserFactory` і витягує product links.  
🔹 Повертає список `Url`, логує успіхи/помилки для подальшого моніторингу.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Базове логування
from typing import List                                             # 📐 Типи публічного API

# 🧩 Внутрішні модулі проєкту
from app.errors.custom_errors import AppError, ParsingError         # ⚠️ Доменно-орієнтовані винятки
from app.domain.products.entities import Url                        # 📦 Канонічний Url
from app.domain.products.interfaces import (
    ICollectionLinksProvider,
    ICollectionProcessingService,
)
from app.infrastructure.parsers.contracts import IParserFactory     # 🏗️ Контракт фабрики парсерів
from app.shared.utils.logger import LOG_NAME                       # 🏷️ Імʼя базового логера
from app.shared.utils.url_parser_service import UrlParserService    # 🔗 Normalization/helpers

logger = logging.getLogger(LOG_NAME)                                # 🧾 Модульний логер сервісу


class CollectionProcessingService(ICollectionProcessingService):
    """⚙️ Оркестратор для витягування посилань із сторінок колекцій."""

    def __init__(self, *, parser_factory: IParserFactory, url_parser: UrlParserService) -> None:
        self._factory = parser_factory                               # 🏗️ Фабрика провайдерів
        self._urls = url_parser                                      # 🔗 Normalization/is_collection helpers
        logger.debug("⚙️ CollectionProcessingService init (factory=%s)", parser_factory)

    async def get_product_links(self, raw_url: str) -> List[Url]:
        logger.info("⚙️ Старт парсингу колекції: %s", raw_url)

        try:
            # 1) Нормалізація та груба перевірка
            normalized = self._urls.normalize(raw_url)               # 🧼 Прибираємо параметри/фрагменти
            logger.debug("🔗 Normalized URL: %s", normalized)
            if not self._urls.is_collection_url(normalized):        # 🚫 Перевіряємо, що це колекція
                raise ParsingError("Посилання не є сторінкою колекції", url=raw_url)

            url = Url(normalized)                                   # 📦 Створюємо доменний Url

            # 2) Провайдер посилань через фабрику
            provider: ICollectionLinksProvider = self._factory.create_collection_provider(url)
            logger.debug("🏭 Провайдер колекції створено: %s", provider)

            # 3) Отримуємо посилання
            links: List[Url] = await provider.get_product_links()   # 📥 Асинхронно тягнемо посилання

            if not links:
                logger.warning("⚠️ Порожня колекція або не знайдені товари: %s", normalized)
            else:
                logger.info("✅ Знайдено посилань: %d (колекція: %s)", len(links), normalized)

            return links

        except AppError as e:
            logger.error(
                "❌ Помилка обробки колекції: %s",
                getattr(e, "message", str(e)),
                extra={"url": raw_url},
            )
            raise
        except Exception as e:                                       # 🔥 Будь-які інші винятки -> ParsingError
            logger.exception("🔥 Непередбачена помилка під час парсингу: %s", raw_url)
            raise ParsingError(
                "Не вдалося обробити сторінку колекції.",
                details=str(e),
                url=raw_url,
            ) from e


__all__ = ["CollectionProcessingService"]
