""" 🚀 main.py — запуск Telegram-бота YoungLA Ukraine.

Цей модуль:
- Ініціалізує Telegram-бота з використанням `python-telegram-bot`
- Реєструє всі обробники команд, посилань та меню
- Забезпечує автоматичне відновлення після помилок мережі

Використовує:
- CurrencyManager — кеш курсів валют + API Monobank
- ConfigService — токен бота з .env
- WebDriverService — управління драйвером для парсингу
- MenuHandler, LinkHandler — обробка меню та посилань
- Усі обробники з bot.handlers
"""

# 🧱 Системне
import time
import sys
import os
import asyncio

# Додає корінь проекта в sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 🌐 Telegram API
from telegram.ext import (
    Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters
)
from telegram.error import TimedOut, NetworkError

# ⚙️ Сервіси
from core.config.config_service import ConfigService

from core.webdriver.webdriver_service import WebDriverService
from core.currency.currency_manager import CurrencyManager

# 🤖 Обробники
from bot.handlers.bot_command_handler import BotCommandHandler
from bot.handlers.size_chart_handler import SizeChartHandlerBot
from bot.handlers.price_calculation_handler import PriceCalculationHandler

# 🛍️ Обробка товарів та колекцій (нова структура)
from bot.handlers.product.product_handler import ProductHandler
from bot.handlers.product.collection_handler import CollectionHandler

# 🛒 Наявність
from core.product_availability.availability_handler import AvailabilityHandler

# 🧭 Маршрути та меню
from bot.menu_handler import MenuHandler
from core.parsers.link_handler import LinkHandler
from bot.keyboards import Keyboard

# 🧾 Логування
from utils.logger import Logger
import logging

# 🔕 Глушим спам от PTB и httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext._application").setLevel(logging.WARNING)
logging.getLogger("telegram.ext._updater").setLevel(logging.WARNING)

# Ініціалізація логера
logger = logging.getLogger(__name__)


class TelegramBot:
    """💬 Основний клас Telegram-бота:
    - Ініціалізує залежності
    - Реєструє всі обробники
    - Запускає бот з підтримкою відновлення
    """

    def __init__(self):
        """🔧 Ініціалізація Telegram-бота та залежностей."""
        self.config = ConfigService()
        self.app = (
            Application.builder()
            .token(self.config.telegram_token)
            .read_timeout(30)
            .write_timeout(30)
            .build()
        )

        # Сервіси
        self.currency_manager = CurrencyManager()
        self.bot_command_handler = BotCommandHandler(self.currency_manager)
        self.product_handler = ProductHandler(self.currency_manager)
        self.collection_handler = CollectionHandler(self.product_handler)
        self.size_chart_handler = SizeChartHandlerBot()
        self.price_calculator = PriceCalculationHandler(self.currency_manager)
        self.availability_handler = AvailabilityHandler()


        # Роутинг
        self.link_handler = LinkHandler(
            currency_manager=self.currency_manager,
            product_handler=self.product_handler,
            collection_handler=self.collection_handler,
            size_chart_handler=self.size_chart_handler,
            price_calculator=self.price_calculator,
            availability_handler = self.availability_handler
        )
        self.menu_handler = MenuHandler()

        self.register_handlers()

    def register_handlers(self):
        """🧾 Реєструє всі обробники:
        - Команди
        - Inline-кнопки
        - Меню
        - Посилання на товари/колекції
        """
        logger.info("🔧 Реєстрація обробників Telegram...")

        # 📌 Стандартні команди
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("rate", self.bot_command_handler.show_current_rate))
        self.app.add_handler(CommandHandler("set_rate", self.bot_command_handler.set_custom_rate))
        self.app.add_handler(CommandHandler("help", self.bot_command_handler.help_command))

        # 📋 Обробка inline-кнопок
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        # 📚 Головне меню
        menu_pattern = (
            "^(🔗 Вставляти посилання товарів|📦 Мої замовлення|📚 Режим колекцій|"
            "💱 Курс валют|📏 Таблиця розмірів|🌍 Перевірити розміри в регіонах|🧮 Режим розрахунку товару|❓ Допомога|⏹️ Вимкнути режим)$"
        )
        self.app.add_handler(MessageHandler(filters.TEXT & filters.Regex(menu_pattern), self.menu_handler.handle_menu))

        # 🔗 Обробка посилань на товари або колекції
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.link_handler.handle_link))

        logger.info("✅ Всі обробники зареєстровані.")

    async def start(self, update, context):
        """🎉 Стартове повідомлення з головним меню."""
        await update.message.reply_text(
            "👋 Вітаю в YoungLA Ukraine Bot! Обери пункт меню 👇",
            reply_markup=Keyboard.main_menu()
        )

    async def button_handler(self, update, context):
        """🎛️ Обробка inline-кнопок (callback_query):
        - Показ курсу
        - FAQ, підтримка
        """
        query = update.callback_query
        await query.answer()

        match query.data:
            case "show_rate":
                await self.bot_command_handler.show_current_rate(update, context)
            case "set_rate":
                await query.edit_message_text("✏️ Введи новий курс у форматі: /set_rate USD 42.5")
            case "faq":
                await query.edit_message_text("📖 Відповіді на часті запитання будуть тут.")
            case "support":
                await query.edit_message_text("📞 Напиши нам у Telegram: @support_username")
            case "help_usage":
                await query.edit_message_text(
                    "📖 <b>Як користуватись ботом?</b>\n\n"
                    "1️⃣ Обери режим через кнопки головного меню.\n"
                    "2️⃣ Надішли посилання на товар чи колекцію.\n"
                    "3️⃣ Бот автоматично розпізнає посилання та відповість детальною інформацією.\n\n"
                    "⏹️ Щоб вийти з режиму — натисни кнопку «Вимкнути режим».",
                    parse_mode="HTML"
                )
            case "help_support":
                await query.edit_message_text(
                    "📞 <b>Зв'язатися з підтримкою:</b>\n\n"
                    "Напиши нам у Telegram: @support_username",
                    parse_mode="HTML"
                )

    def run(self, max_retries=5):
        """🚀 Запускає Telegram-бота з перезапуском у разі помилок."""
        attempt = 0
        while attempt < max_retries:
            try:
                logger.info("🚀 Запускаю Telegram-бота...")
                self.app.run_polling()
                break
            except TimedOut:
                attempt += 1
                logger.warning(f"⚠️ Тайм-аут. Повторна спроба {attempt}/{max_retries}...")
                time.sleep(5)
            except NetworkError as e:
                logger.error(f"❌ Помилка мережі: {e}. Перезапуск через 10 секунд...")
                time.sleep(10)
            except Exception as e:
                logger.critical(f"🔥 Критична помилка: {e}")
                break
            
        logger.info("🛑 Бота зупинено.")
        asyncio.run(WebDriverService.close_browser())
    


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
