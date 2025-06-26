"""
🧾 ProductMessageBuilder — клас для генерації опису товару, хештегів, перекладу та цінового повідомлення.
🔹 Використовує:
- TranslatorService для генерації слогану та перекладу опису
- HashtagGenerator для створення хештегів
- PriceCalculationHandler для розрахунку ціни та формування повідомлення про ціну
"""

# 🧠 Генерація контенту
from bot.content.translator import TranslatorService
from bot.content.hashtag_generator import HashtagGenerator

# 💰 Валюти та розрахунки
from bot.handlers.price_calculation_handler import PriceCalculationHandler

# 🧱 Системні
import asyncio
import logging

logger = logging.getLogger(__name__)

class ProductMessageBuilder:
    """
    🧱 Клас, що відповідає за повну генерацію текстового контенту для товару:
    - Опис товару у вигляді HTML-повідомлення
    - Слоган, хештеги, переклад характеристик
    - Розрахунок ціни та отримання зображень

    🔧 Залежності:
    - currency_manager: передається до PriceCalculationHandler
    """

    def __init__(self, currency_manager):
        """
        🔨 Ініціалізує сервіси генерації:
        - TranslatorService — переклад і генерація слогану
        - HashtagGenerator — підбір релевантних хештегів
        - PriceCalculationHandler — розрахунок ціни товару

        :param currency_manager: Менеджер валют для доступу до курсів
        """
        self.translator = TranslatorService()
        self.hashtag_generator = HashtagGenerator()
        self.price_handler = PriceCalculationHandler(currency_manager)

    async def generate_content(self, title: str, description: str, image_url: str, url: str, colors_text: str) -> tuple:
        """
        🎨 Генерує контент для товару (слоган, хештеги, переклад опису та повідомлення з ціною).
        Повертає кортеж: (description_text, price_message, images).
        """
        logger.info(f"🧠 Генерація контенту для товару: {title}")

        # ⚙️ Паралельний запуск генерації слогану, хештегів, перекладу та розрахунку ціни
        slogan_task = asyncio.to_thread(self.translator.generate_slogan, title, description)
        translate_task = asyncio.to_thread(self.translator.translate_text, description)
        hashtags_task = self.hashtag_generator.generate(title, description)
        price_task = self.price_handler.calculate_and_format(url)

        try:
            slogan, sections, hashtags, (region, price_message, images) = await asyncio.gather(
                slogan_task,
                translate_task,
                hashtags_task,
                price_task
            )
        except Exception as e:
            logger.error(f"❌ Помилка під час генерації контенту для товару '{title}': {e}")
            raise

        logger.info(f"✅ Контент успішно згенеровано для: {title}")

        # Формуємо текст опису товару з отриманих даних
        description_text = self._build_description(title, colors_text, slogan, hashtags, sections)
        return description_text, price_message, images

    # --- 🧩 Приватні допоміжні методи ---
    @staticmethod
    def _build_description(title: str, colors_text: str, slogan: str, hashtags: str, sections: dict) -> str:
        """
        📝 Створює HTML-опис товару, включаючи характеристики, доступні кольори, слоган та хештеги.

        :param title: Назва товару
        :param colors_text: Текст з кольорами і розмірами та регіональною доступністю
        :param slogan: Згенерований слоган
        :param hashtags: Згенеровані хештеги
        :param sections: Перекладені блоки опису
        :return: Готовий HTML-текст
        """
        material = sections.get("МАТЕРІАЛ", "Немає даних")
        fit = sections.get("ПОСАДКА", "Немає даних")
        description = sections.get("ОПИС", "Немає даних")
        model = sections.get("МОДЕЛЬ", "Немає даних")

        # 🛒 Реальна перевірка на розпродаж за позначками ❌ в кольорах
        sold_out = all("❌" in line for line in colors_text.splitlines())
        title_display = f"❌ РОЗПРОДАНО ❌\n\n{title.upper()}" if sold_out else title.upper()

        return (
            f"<b>{title_display}:</b>\n\n"
            f"<b>МАТЕРІАЛ:</b> {material}\n"
            f"<b>ПОСАДКА:</b> {fit}\n"
            f"<b>ОПИС:</b> {description}\n\n"
            f"{colors_text}\n\n"
            f"<b>МОДЕЛЬ:</b> {model}\n\n"
            f"<b>{slogan}</b>\n\n"
            f"<b>{hashtags}</b>"
        )
