# 🧠 app/infrastructure/content/product_content_service.py
"""
🧠 product_content_service.py — сервіс для агрегації контенту про товар.

🔹 Клас `ProductContentService`:
- Асинхронно збирає дані з різних джерел (AI, ціни, наявність).
- Повертає структурований об'єкт з усіма даними для подальшого форматування.
"""

# 🔠 Системні імпорти
import asyncio                                                    # 🔄 Паралельне виконання задач
import logging                                                    # 🧾 Логування
from dataclasses import dataclass                                 # 📦 Структуровані DTO
from typing import Dict, List, Tuple                              # 🧩 Типи даних

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.ai.translator import TranslatorService                # 🤖 AI-переклад і генерація
from app.infrastructure.content.hashtag_generator import HashtagGenerator     # 🏷️ Генерація хештегів
from app.infrastructure.telegram.handlers.price_calculator_handler import PriceCalculationHandler  # 💰 Розрахунок ціни
from app.shared.utils.logger import LOG_NAME                                  # 📒 Імʼя логера

logger = logging.getLogger(LOG_NAME)

# ================================
# 📦 DTO ДЛЯ КОНТЕНТУ ТОВАРУ
# ================================
@dataclass(frozen=True)
class ProductContentDTO:
    """
    📦 Data Transfer Object для контенту одного товару.
    Забезпечує уніфіковану структуру для подальшого форматування в повідомлення.
    """
    title: str                                                    # 🏷️ Назва товару
    slogan: str                                                   # 💬 Короткий слоган
    hashtags: str                                                 # #️⃣ Хештеги
    sections: Dict[str, str]                                      # 📚 Перекладені секції опису
    colors_text: str                                              # 🎨 Опис кольорів
    price_message: str                                            # 💸 Розрахована вартість
    images: List[str]                                             # 🖼️ Список URL зображень

# ================================
# 🏛️ КЛАС СЕРВІСУ АГРЕГАЦІЇ
# ================================
class ProductContentService:
    """
    🧠 Сервіс, що відповідає за збір усього текстового та медіа-контенту для товару.
    """
    def __init__(
        self,
        translator_service: TranslatorService,                                    # 🤖 Перекладач (GPT)
        hashtag_generator: HashtagGenerator,                                      # 🏷️ Генератор хештегів
        price_handler: PriceCalculationHandler,                                   # 💰 Обчислення вартості
    ):
        self.translator = translator_service                                      # 📥 Зберігаємо залежність
        self.hashtag_generator = hashtag_generator
        self.price_handler = price_handler

    async def build_product_content(
        self,
        title: str,
        description: str,
        image_url: str,
        url: str,
        colors_text: str
    ) -> ProductContentDTO:
        """
        📦 Агрегує весь контент, виконуючи запити паралельно.

        Args:
            title (str): Назва товару
            description (str): Оригінальний опис з сайту
            image_url (str): Головне зображення товару
            url (str): Посилання на товар
            colors_text (str): Витягнуті кольори у текстовій формі

        Returns:
            ProductContentDTO: Повністю зібраний структурований контент
        """
        logger.info(f"🧠 Починаю побудову контенту для: {title}")

        # 🧠 Запускаємо генерацію в паралельних потоках
        slogan_task = asyncio.to_thread(self.translator.generate_slogan, title, description)       # 💬 Слоган
        translate_task = asyncio.to_thread(self.translator.translate_text, description)            # 🌐 Переклад опису
        hashtags_task = self.hashtag_generator.generate(title, description)                        # 🏷️ Хештеги
        price_task = self.price_handler.calculate_and_format(url)                                  # 💰 Ціна + зображення

        try:
            # ⏳ Чекаємо завершення всіх задач паралельно
            slogan, sections, hashtags, (_, price_message, images) = await asyncio.gather(
                slogan_task,
                translate_task,
                hashtags_task,
                price_task
            )
        except Exception as e:
            logger.error(f"❌ Помилка під час побудови контенту для '{title}': {e}")
            raise

        logger.info(f"✅ Контент успішно збудовано для: {title}")

        return ProductContentDTO(
            title=title,                            # 🏷️ Назва товару
            slogan=slogan,                          # 💬 Згенерований слоган
            hashtags=hashtags,                      # 🏷️ Згенеровані хештеги
            sections=sections,                      # 📚 Переклад опису
            colors_text=colors_text,                # 🎨 Кольори як текст
            price_message=price_message,            # 💸 Форматована вартість
            images=images                           # 🖼️ Список зображень
        )