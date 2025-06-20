# 📏 size_chart_handler_bot.py — обробник команди /size_chart в Telegram-боті.

"""
🔹 Парсить HTML-код товару (або приймає готовий page_source)
🔹 Витягує таблицю розмірів
🔹 Генерує зображення таблиці
🔹 Надсилає у Telegram

Використовує:
- ProductParser — для отримання HTML-сторінки
- SizeChartHandler — для пошуку таблиці і генерації зображення
"""

# 🧱 Системні
import logging

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🛒 Парсинг товару
from core.parsing.base_parser import BaseParser

# 🛠️ Інше
from errors.error_handler import error_handler

# 📏 Таблиця розмірів
from size_chart.size_chart_handler import SizeChartHandler


class SizeChartHandlerBot:
    """📏 Обробник таблиці розмірів для товарів YoungLA.

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
        page_source: str = None,
    ):
        """📬 Основний метод обробки команди /size_chart.

        :param update: Об'єкт Telegram Update
        :param context: Контекст виконання команди
        :param url: Посилання на товар (може бути отримане з context.args)
        :param page_source: Готовий HTML-код сторінки (якщо переданий)
        """
        url = await SizeChartHandlerBot._resolve_url(update, context, url)
        if not url:
            return

        logging.info(f"📏 Запит таблиць розмірів для: {url}")

        page_source = await SizeChartHandlerBot._get_page_source(url, page_source)
        if not page_source:
            await update.message.reply_text("❌ Не вдалося завантажити сторінку товару.")
            return

        images = await SizeChartHandlerBot._generate_all_size_charts(url, page_source)
        if not images:
            await update.message.reply_text("⚠️ Таблиці розмірів не знайдено.")
            return

        await SizeChartHandlerBot._send_size_chart_images(update, images)

    # --- ⬇️ Приватні допоміжні методи ⬇️ ---

    @staticmethod
    async def _resolve_url(update: Update, context: CallbackContext, url: str = None) -> str:
        """🧭 Отримує посилання з context або повідомлення."""
        if url:
            return url
        if context.args:
            return context.args[0]
        await update.message.reply_text("❌ Укажіть посилання на товар після команди.")
        return None

    @staticmethod
    async def _get_page_source(url: str, page_source: str = None) -> str:
        """🌐 Завантажує HTML-сторінку, якщо не передана."""
        if page_source:
            return page_source
        logging.warning("⚠️ Відсутній page_source, виконується завантаження...")
        parser = BaseParser(url)
        await parser.fetch_page()
        return parser.page_source

    @staticmethod
    async def _generate_all_size_charts(url: str, page_source: str) -> list[str]:
        """🖼️ Генерує всі таблиці розмірів (по можливості кілька)."""
        handler = SizeChartHandler(url, page_source)
        return await handler.process_all_size_charts()

    @staticmethod
    async def _send_size_chart_images(update: Update, image_paths: list[str]):
        """📤 Надсилає всі зображення таблиць розмірів по черзі."""
        for i, path in enumerate(image_paths, 1):
            try:
                with open(path, "rb") as img_file:
                    caption = f"📏 Таблиця розмірів ({i} з {len(image_paths)})"
                    await update.message.reply_photo(photo=img_file, caption=caption)
            except Exception as e:
                logging.error(f"❌ Помилка при відправці таблиці №{i}: {e}")
                await update.message.reply_text(f"⚠️ Помилка при відправці таблиці №{i}")