# 📏 app/bot/handlers/size_chart_handler_bot.py
"""
📏 size_chart_handler_bot.py — Обробник команди для генерації таблиць розмірів.

🔹 Клас `SizeChartHandlerBot`:
    • Отримує посилання або HTML-сторінку товару
    • Завантажує HTML при необхідності (через парсер)
    • Делегує обробку таблиць сервісу SizeChartService
    • Відправляє зображення через SizeChartMessenger
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update											                        # 🤖 Telegram-API
from telegram.ext import CallbackContext								                    # ⌨️ Контекст команди

# 🔠 Системні імпорти
import logging																                # 🧾 Логування
from typing import Optional												                    # 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.errors.error_handler import error_handler							                # ❗ Декоратор для обробки помилок
from app.infrastructure.parsers.parser_factory import ParserFactory				            # 🏭 Фабрика парсерів
from app.infrastructure.size_chart.size_chart_service import SizeChartService		        # 📐 Сервіс генерації таблиць
from app.bot.ui.size_chart_messenger import SizeChartMessenger				                # ✉️ Модуль надсилання повідомлень

logger = logging.getLogger(__name__)

# ================================
# 🤖 КЛАС ОБРОБНИКА ДЛЯ БОТА
# ================================
class SizeChartHandlerBot:
    """ 🤖 Обробляє запити на таблиці розмірів, делегуючи роботу сервісам. """

    def __init__(
        self,
        parser_factory: ParserFactory,
        size_chart_service: SizeChartService,
        messenger: SizeChartMessenger,
    ):
        self.parser_factory = parser_factory										                    # 🏭 Створення парсерів
        self.size_chart_service = size_chart_service								                    # 📐 Генерація таблиць
        self.messenger = messenger												                        # ✉️ Надсилання повідомлень

    @error_handler
    async def size_chart_command(
        self,
        update: Update,
        context: CallbackContext,
        url: Optional[str] = None,
        page_source: Optional[str] = None,
    ):
        """ 📬 Обробляє запит на отримання таблиць розмірів. """
        if not update.message:
            return															                            # 🚫 Немає повідомлення — нічого робити

        final_url = url or (context.args[0] if context.args else None)				                    # 🔗 Отримуємо URL з аргументів або параметра
        if not final_url:
            await update.message.reply_text("❌ Будь ласка, вкажіть посилання на товар.")		       # 📝 Підказка користувачу
            return

        logging.info(f"📏 Запит таблиць розмірів для: {final_url}")					                    # 🧾 Лог запиту

        if not page_source:
            parser = self.parser_factory.create_product_parser(final_url, enable_progress=False)	    # 🧠 Ініціалізуємо парсер без прогрес-бару
            await parser.get_product_info()									                            # 🌐 Завантажуємо HTML сторінки
            page_source = parser.page_source									                        # 🧽 Зберігаємо HTML для аналізу

        if not page_source:
            await update.message.reply_text("❌ Не вдалося завантажити сторінку товару.")		        # 🚫 Відсутній HTML — помилка
            return

        image_paths = await self.size_chart_service.process_all_size_charts(page_source)		        # 📐 Генеруємо таблиці з HTML
        await self.messenger.send(update, image_paths)						                            # ✉️ Надсилаємо результати користувачу