""" 📏 size_chart_handler_bot.py — обробник команди /size_chart в Telegram-боті.

🔹 Парсить HTML-код товару (або приймає готовий page_source)
🔹 Витягує таблицю розмірів
🔹 Генерує зображення таблиці
🔹 Надсилає у Telegram

Використовує:
- ProductParser — для отримання HTML-сторінки
- SizeChartHandler — для пошуку таблиці і генерації зображення
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🛒 Парсинг товару
from core.parsing.parser import ProductParser

# 📏 Таблиця розмірів
from size_chart.size_chart_handler import SizeChartHandler

# 🛠️ Інше
from errors.error_handler import error_handler

# 🧱 Системні
import logging

class SizeChartHandlerBot:
    """ 📏 Обробник таблиці розмірів для товарів YoungLA.
    
    🔹 Приймає посилання на товар або готовий HTML-код
    🔹 Витягує таблицю розмірів
    🔹 Генерує зображення та надсилає в Telegram
    """

    @staticmethod
    @error_handler
    async def size_chart_command(
        update: Update,
        context: CallbackContext,
        url: str = None,
        page_source: str = None
    ):
        """ 📬 Основний метод обробки команди /size_chart.
        
        :param update: Об'єкт Telegram Update
        :param context: Контекст виконання команди
        :param url: Посилання на товар (може бути отримане з context.args)
        :param page_source: Готовий HTML-код сторінки (якщо переданий)
        """
        url = await SizeChartHandlerBot._resolve_url(update, context, url)
        if not url:
            return

        logging.info(f"📏 Запит таблиці розмірів для: {url}")

        page_source = await SizeChartHandlerBot._get_page_source(url, page_source)
        if not page_source:
            await update.message.reply_text("❌ Не вдалося завантажити сторінку товару.")
            return

        image_path = await SizeChartHandlerBot._generate_size_chart(url, page_source)
        if not image_path:
            await update.message.reply_text("⚠️ Не знайдено таблицю розмірів.")
            return

        await SizeChartHandlerBot._send_size_chart_image(update, image_path)

    # --- ⬇️ Приватні допоміжні методи ⬇️ ---

    @staticmethod
    async def _resolve_url(update: Update, context: CallbackContext, url: str = None) -> str:
        """ 🧭 Отримує посилання з context або повідомлення.
        """
        if url:
            return url
        if context.args:
            return context.args[0]
        await update.message.reply_text("❌ Укажіть посилання на товар після команди.")
        return None


    @staticmethod
    async def _get_page_source(url: str, page_source: str = None) -> str:
        """ 🌐 Завантажує HTML-сторінку, якщо не передана.
        """
        if page_source:
            return page_source
        logging.warning("⚠️ Відсутній page_source, виконується завантаження...")
        parser = ProductParser(url)
        await parser.parser.fetch_page()
        return parser.page_source

    @staticmethod
    async def _generate_size_chart(url: str, page_source: str) -> str:
        """ 🖼️ Генерує зображення таблиці розмірів.
        """
        handler = SizeChartHandler(url, page_source)
        return await handler.process_size_chart()

    @staticmethod
    async def _send_size_chart_image(update: Update, image_path: str):
        """ 📤 Надсилає таблицю розмірів у Telegram.
        """
        try:
            with open(image_path, "rb") as img_file:
                await update.message.reply_photo(photo=img_file, caption="📏 Таблиця розмірів (в сантиметрах)")
        except Exception as e:
            logging.error(f"❌ Не вдалося відправити зображення: {e}")
            await update.message.reply_text("⚠️ Помилка при відправці зображення.")
