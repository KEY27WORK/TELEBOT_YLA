# 🧾 app/bot/handlers/product/collection_handler.py
"""
🧾 CollectionHandler — обробка колекцій товарів YoungLA.
"""

# 🌐 Telegram API
from telegram import Update                                                                                         # 📩 Оновлення з чату
from telegram.ext import CallbackContext                                                                            # 📥 Контекст виклику обробника

# 🔠 Системні імпорти
import asyncio                                                                                                      # ⏱️ Асинхронна затримка між товарами
import logging                                                                                                      # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                                                                             # ⚙️ Конфігурація
from app.infrastructure.currency.currency_manager import CurrencyManager                                                        # 💱 Менеджер валют
from app.errors.error_handler import error_handler                                                                              # ❌ Декоратор обробки помилок
from app.shared.utils.url_parser_service import UrlParserService                                                                # 🌍 Визначення регіону сайту
from .product_handler import ProductHandler                                                                                     # 🛍️ Обробка окремого товару
from app.infrastructure.collection_processing.collection_processing_service import CollectionProcessingService                  # 📚 Парсинг колекцій

logger = logging.getLogger(__name__)


# ================================
# 🏛️ КЛАС ОБРОБНИКА КОЛЕКЦІЙ
# ================================
class CollectionHandler:
    """
    📦 Обробляє колекції товарів для Telegram-бота YoungLA Ukraine.
    """

    def __init__(
        self,
        product_handler: ProductHandler,
        currency_manager: CurrencyManager,
        url_parser_service: UrlParserService,
        config_service: ConfigService,
        collection_processing_service: CollectionProcessingService,
    ):
        self.product_handler = product_handler								                                        # 🛍️ Обробник одного товару
        self.currency_manager = currency_manager							                                        # 💱 Оновлення валют
        self.url_parser_service = url_parser_service						                                        # 🌍 Регіон (us/eu/uk)
        self.collection_processing_service = collection_processing_service			                                # 📚 Парсер колекції

        self._delay_sec = config_service.get("collection_processing_delay_sec", 2)                                  # ⏱️ Затримка між товарами
        self._progress_interval = config_service.get("collection_progress_update_interval", 5)                      # 🕓 Інтервал для повідомлення про прогрес

        logger.info("🔧 CollectionHandler ініціалізовано")

    # ================================
    # 📩 ОБРОБКА КОЛЕКЦІЇ
    # ================================
    @error_handler
    async def handle_collection(self, update: Update, context: CallbackContext):
        """
        📩 Приймає посилання на колекцію та обробляє всі товари в ній.
        """
        if not update.message or not context.user_data:
            return

        url = context.user_data.get("url") or update.message.text.strip()                                           # 🔗 Отримуємо URL
        logger.info(f"📩 Отримано посилання на колекцію: {url}")

        self.currency_manager.update_all_rates()                                                                    # 💱 Оновлюємо курси

        try:
            region_display = self.url_parser_service.get_region(url)                                                # 🌍 Визначаємо регіон
            await update.message.reply_text(
                f"🌍 Регіон колекції: <b>{region_display}</b>", parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text("❌ Не вдалося розпізнати регіон сайту.")
            return

        product_links = await self.collection_processing_service.get_product_links(url)                             # 📚 Отримуємо товари з колекції

        if not product_links:
            await update.message.reply_text("❌ Не вдалося знайти товари в цій колекції.")
            return

        await update.message.reply_text(f"🔍 Знайдено {len(product_links)} товарів. Починаю обробку...")
        await self._process_each_product(update, context, product_links)                                            # 🔁 Обробка кожного товару
        logger.info("✅ Завершено обробку всіх товарів з колекції.")

    # ================================
    # 🔄 ПОСЛІДОВНА ОБРОБКА ТОВАРІВ
    # ================================
    async def _process_each_product(
        self,
        update: Update,
        context: CallbackContext,
        product_links: list[str],
    ):
        """
        🔄 Послідовно обробляє кожен товар із колекції та інформує про прогрес.
        """
        total_products = len(product_links)
        for i, product_url in enumerate(product_links, start=1):
            logger.info(f"📦 Обробляю товар {i}/{total_products}: {product_url}")

            await self.product_handler.handle_url(
                update,
                context,
                product_url,
                update_currency=False,
            )

            if i % self._progress_interval == 0 and i < total_products:
                await update.message.reply_text(f"⏳ Оброблено {i}/{total_products} товарів...")                # 📢 Прогрес через кожні N товарів

            if i < total_products:
                await asyncio.sleep(self._delay_sec)                                                            # ⏱️ Затримка між товарами
