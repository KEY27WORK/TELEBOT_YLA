# 🧠 app/infrastructure/content/product_content_service.py
"""
🧠 Сервіс агрегує контент для картки товару (слоган, переклади, хештеги, ціна, ALT).

🔹 «ProductContentService» координує AI-запити, побічні генератори та форматування ціни.  
🔹 Повертає строго типізований `ProductContentDTO`, придатний до подальшого відображення.  
🔹 Виключення не ковтаються — оркестратор має побачити збій (вимога IMP-011).
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio                                                      # 🔄 Паралельні виклики
import logging                                                      # 🧾 Журналювання стану
from dataclasses import dataclass                                   # 📦 DTO
from typing import Dict, List, Optional, TYPE_CHECKING             # 📐 Типи

# 🧩 Доменні контракти
from app.domain.ai.task_contracts import ITextAI                    # 🤖 Генератор текстів
from app.domain.content.interfaces import IHashtagGenerator         # 🏷️ Контракт хештегів
from app.domain.products.entities import ProductInfo                # 📦 Дані продукту

# 🧰 Інфраструктура / адаптери
from app.infrastructure.adapters import (                           # 🔗 Компонування фасадів
    HashtagGeneratorStringAdapter,                                  # Set[str] -> str
    IPriceMessageFacade,                                            # 💸 Фасад ціни
    PriceMessageFacade,
)
from app.infrastructure.content.alt_text_generator import AltTextGenerator  # 🖼️ ALT-тексти
from app.shared.utils.logger import LOG_NAME                        # 🏷️ Імʼя логера

if TYPE_CHECKING:                                                   # 🧠 Лише для типізації
    from app.bot.handlers.price_calculator_handler import PriceCalculationHandler

logger = logging.getLogger(LOG_NAME)                                # 🧾 Модульний логер


# ================================
# 📦 DTO ДЛЯ КОНТЕНТУ
# ================================
@dataclass(frozen=True, slots=True)
class ProductContentDTO:
    title: str                                                       # 🏷️ Назва товару
    slogan: str                                                      # 💬 Слоган від AI
    hashtags: str                                                    # #️⃣ Хештеги рядком
    sections: Dict[str, str]                                         # 📚 Перекладені секції
    colors_text: str                                                 # 🎨 Опис наявності
    price_message: str                                               # 💸 Повідомлення ціни
    images: List[str]                                                # 🖼️ URL зображень
    alt_texts: Dict[str, str]                                        # 🔎 ALT-тексти url → alt


__all__ = ["ProductContentDTO", "ProductContentService"]


# ================================
# 🏛️ СЕРВІС АГРЕГАЦІЇ
# ================================
class ProductContentService:
    """🧠 Координує текст/медіа-дані для `ProductInfo`."""

    def __init__(
        self,
        translator: ITextAI,
        hashtag_generator: IHashtagGenerator,
        price_handler: "PriceCalculationHandler",
        alt_text_generator: Optional[AltTextGenerator] = None,
    ) -> None:
        self._translator = translator                                 # 🤖 Переклад/слогани
        self._hashtags = HashtagGeneratorStringAdapter(hashtag_generator)  # 🏷️ → str
        self._price: IPriceMessageFacade = PriceMessageFacade(price_handler)  # 💸 Фасад ціни
        self._alt = alt_text_generator                                # 🖼️ ALT (необов'язково)
        logger.debug(
            "⚙️ ProductContentService init (alt=%s)",
            bool(alt_text_generator),
        )

    async def build_product_content(
        self,
        product: ProductInfo,
        *,
        url: str,
        colors_text: str,
    ) -> ProductContentDTO:
        """📦 Агрегує всі поля DTO та повертає `ProductContentDTO`."""
        logger.info("🧠 Початок побудови контенту для: %s", product.title)

        slogan_task = self._translator.generate_slogan(               # 💬 Слоган
            title=product.title,
            description=product.description,
        )
        translate_task = self._translator.translate_sections(        # 🌐 Переклад секцій
            text=product.description,
        )
        hashtags_task = self._hashtags.generate(product)              # 🏷️ Хештеги рядком
        price_task = self._price.calculate_and_format(url)            # 💸 Повідомлення ціни

        try:
            slogan, sections, hashtags, price_tuple = await asyncio.gather(
                slogan_task,
                translate_task,
                hashtags_task,
                price_task,
            )                                                         # ⏳ Паралельне очікування
            logger.debug(
                "📦 gather done: slogan=%s, sections=%s, hashtags_len=%d",
                bool(slogan),
                len(sections) if isinstance(sections, dict) else -1,
                len(hashtags) if isinstance(hashtags, str) else -1,
            )
        except asyncio.CancelledError:
            logger.info("🛑 Побудову контенту скасовано для: %s", product.title)  # 🛑 propagate cancel
            raise
        except Exception as exc:
            logger.exception("❌ Збій під час побудови контенту для '%s'", product.title)  # 🧯 лог для оркестратора
            raise

        if not isinstance(price_tuple, tuple) or len(price_tuple) < 3:  # 📏 гарантований контракт price-фасаду
            logger.error("💥 Price facade повернув: %r", price_tuple)
            raise ValueError("Price facade returned unexpected shape.")
        _, price_message, images = price_tuple                        # 📤 Розпаковуємо результат
        logger.debug("💸 Price facade images=%d", len(images) if isinstance(images, list) else -1)  # 🧾 логимо метадані

        if not isinstance(sections, dict):                            # 🛡️ гарантуємо очікувані типи
            raise TypeError("Translator повернув не dict.")
        if not isinstance(hashtags, str):
            raise TypeError("Hashtag adapter повинен повертати рядок.")
        if not isinstance(images, list):
            images = list(product.images or [])                       # 🛟 Фолбек на зображення з продукту

        alt_texts: Dict[str, str] = {}                                # 🔎 ALT-тексти за замовчуванням порожні
        image_candidates = [img for img in images if isinstance(img, str) and img]  # 🖼️ нормалізуємо URL
        if not image_candidates:
            image_candidates = [img for img in (product.images or ()) if isinstance(img, str) and img]  # ↩️ fallback

        if self._alt and image_candidates:
            try:
                alt_texts = await self._alt.generate(product, tuple(image_candidates))  # 🤖 генеруємо ALT
                logger.debug("🔎 ALT-тексти згенеровано: %d", len(alt_texts))  # 📊 скільки отримали
            except asyncio.CancelledError:
                logger.info("🛑 ALT-генерацію скасовано для: %s", product.title)  # 🛑 propagate cancel
                raise
            except Exception as alt_err:
                logger.warning("⚠️ ALT-генерація не вдалася: %s", alt_err)  # ⚠️ не валимо пайплайн
                alt_texts = {}                                            # ↩️ Порожні ALT

        raw_parser_sections: Dict[str, str] = {
            str(k): str(v)
            for k, v in dict(product.sections or {}).items()
            if isinstance(k, str) and isinstance(v, str)
        }                                                             # 🧾 Оригінальні секції з парсера (англ)
        translated_sections: Dict[str, str] = {
            str(k): str(v)
            for k, v in sections.items()
            if isinstance(k, str) and isinstance(v, str)
        }                                                             # 🌐 Перекладені (AI) секції

        merged_sections: Dict[str, str] = dict(raw_parser_sections)   # 🔁 Починаємо з даних парсера
        for key, value in translated_sections.items():
            cleaned_value = value.strip()
            if cleaned_value:                                         # 🧼 Уникаємо порожніх перезаписів
                merged_sections[key] = cleaned_value                  # 🔄 Переклад має пріоритет

        dto = ProductContentDTO(
            title=product.title or "",
            slogan=slogan or "",
            hashtags=hashtags or "",
            sections=merged_sections,
            colors_text=colors_text or "",
            price_message=price_message or "",
            images=image_candidates,
            alt_texts=alt_texts,
        )
        logger.info("✅ Контент збудовано: %s", product.title)
        return dto
