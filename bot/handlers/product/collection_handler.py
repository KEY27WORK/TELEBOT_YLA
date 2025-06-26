'''
🧾 CollectionHandler — обробка колекцій товарів YoungLA.
🔹 Основні функції:
- Парсить посилання на колекцію та визначає регіон сайту
- Отримує список товарів в колекції
- Використовує ProductHandler для обробки кожного товару в колекції

☑️ Відповідає принципам SOLID:
- SRP: кожен метод виконує одну чітку задачу
- DIP: використовує ProductHandler як залежність
'''

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🛍️ Парсинг колекцій
from core.parsers.parser_factory import ParserFactory

# 💰 Валюти та розрахунки
from core.currency.currency_manager import CurrencyManager

# ⚙️ Інше
from errors.error_handler import error_handler
from .product_handler import ProductHandler
from core.product_availability.availability_handler import AvailabilityHandler  

# 🧱 Системні
import asyncio
import logging

logger = logging.getLogger(__name__)


class CollectionHandler:
    """
    📦 Обробник колекцій товарів для Telegram-бота YoungLA Ukraine.

    🔹 Основні завдання:
    - Отримання посилання на колекцію
    - Парсинг усіх товарів у колекції
    - Виклик ProductHandler для кожного товару

    ☑️ Використовує:
    - ProductHandler — для обробки кожного окремого товару
    - CurrencyManager — для оновлення курсу перед обробкою
    """

    def __init__(self, product_handler: ProductHandler = None, currency_manager: CurrencyManager = None):
        """
        🔧 Ініціалізація обробника колекцій.

        :param product_handler: Інстанс обробника окремих товарів
        :param currency_manager: Менеджер валют (якщо не передано — створюється новий)
        """
        self.currency_manager = currency_manager or CurrencyManager()
        self.product_handler = product_handler or ProductHandler(self.currency_manager)
        logger.info("🔧 CollectionHandler ініціалізовано")
   
    @error_handler
    async def handle_collection(self, update: Update, context: CallbackContext):
        """
        📩 Основний метод: приймає посилання на колекцію, обробляє всі товари в ній.
        """
        url = update.message.text.strip()
        logger.info(f"📩 Отримано посилання на колекцію: {url}")

        # 💱 Оновлюємо курси валют перед обробкою
        self.currency_manager.update_rate()
        collection_parser = ParserFactory.get_collection_parser(url)

        region = collection_parser.get_currency()

        await self.send_region_info(update, region)
        product_links = await collection_parser.extract_product_links()

        if not product_links:
            await update.message.reply_text("❌ Не вдалося знайти товари в цій колекції.")
            logger.warning("⚠️ Колекція порожня.")
            return

        await update.message.reply_text(f"🔍 Знайдено {len(product_links)} товарів. Починаю обробку...")

        await self.process_each_product(update, context, product_links)
        logger.info("✅ Завершено обробку всіх товарів з колекції.")

    async def send_region_info(self, update: Update, region: str):
        """
        🌍 Надсилає повідомлення з регіоном колекції (напр. US/EU/UK).
        """
        await update.message.reply_text(f"🌍 Регіон колекції: <b>{region}</b>", parse_mode="HTML")
        logger.info(f"🌍 Регіон колекції: {region}")

    async def process_each_product(self, update: Update, context: CallbackContext, product_links: list[str]):
        """
        🔄 Послідовно обробляє кожен товар з отриманого списку посилань.
        """
        for i, product_url in enumerate(product_links):
            logger.info(f"📦 Обробляю товар {i + 1}/{len(product_links)}: {product_url}")
            await self.product_handler.handle_url(update, context, product_url, update_currency=False)
            await asyncio.sleep(2)  # ⏳ Коротка пауза між обробкою товарів