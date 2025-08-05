# 🔗 app/bot/handlers/link_handler.py
"""
🔗 link_handler.py — Головний маршрутизатор для обробки посилань та тексту.

🔹 Клас `LinkHandler`:
- Приймає текст або посилання від користувача.
- Делегує обробку запиту відповідним приватним методам.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update                                                 # 📩 Повідомлення від Telegram
from telegram.ext import CallbackContext                                    # 🔁 Контекст з callback'ом

# 🔠 Системні імпорти
import re                                                                   # 🔤 Регулярки для перевірки запитів
from typing import Any, Dict, Optional, Callable, Awaitable                 # 🧰 Типи
from functools import wraps                                                 # 🪄 Декоратор

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.collection_handler import CollectionHandler                               # 📚 Обробник колекцій
from app.bot.handlers.product.product_handler import ProductHandler                                     # 🛍️ Обробник товарів
from app.bot.handlers.size_chart_handler_bot import SizeChartHandlerBot                                 # 📏 Таблиця розмірів
from app.config.setup import constants as const                                                         # ⚙️ Константи режимів
from app.domain.products.interfaces import IProductSearchProvider                                       # 🔍 Резолвер пошуку
from app.errors.error_handler import error_handler                                                      # 🧯 Декоратор помилок
from app.infrastructure.availability.availability_handler import AvailabilityHandler                    # 🌍 Обробка наявності
from app.infrastructure.currency.currency_manager import CurrencyManager                                # 💱 Менеджер валют
from app.infrastructure.telegram.handlers.price_calculator_handler import PriceCalculationHandler       # 🧮 Обробка ціни
import logging											            # 🧾 Логування подій
from app.shared.utils.logger import LOG_NAME                       # ⚙️ Назва логера з проєкту
from app.shared.utils.url_parser_service import UrlParserService                                        # 🔗 Визначення типу URL

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)                               # 🧾 Логер для реєстрації подій


# ================================
# 🔎 ДОПОМІЖНІ ФУНКЦІЇ ТА ДЕКОРАТОРИ
# ================================

def is_valid_search_query(text: str) -> bool:
    """🧠 Перевірка валідності текстового запиту для пошуку."""
    if len(text) < 3: return False                                                          # ⛔ Надто короткий запит
    if not re.fullmatch(r"[A-Za-z0-9\s\-]+", text): return False                            # 🔤 Лише латиниця, пробіли, дефіси
    if re.search(r"[а-яА-ЯёЁіІїЇєЄ]|[\U0001F600-\U0001F64F]", text): return False           # 🚫 Без кирилиці та emoji
    return True

def product_url_required(func: Callable[..., Awaitable[None]]):
    """🛡️ Декоратор: перевіряє, чи є URL посиланням на товар."""
    @wraps(func)
    async def wrapper(self: "LinkHandler", update: Update, context: CallbackContext, url: str):
        if not update.message:
            return
        logger.debug(f"🔒 Перевірка URL на відповідність товарному: {url}")
        if self.url_parser_service.is_product_url(url):
            return await func(self, update, context, url=url)
        else:
            await update.message.reply_text("❌ Для цієї операції потрібне посилання на товар.")
    return wrapper


# ================================
# 🔗 КЛАС-МАРШРУТИЗАТОР ЗАПИТІВ
# ================================
class LinkHandler:
    """
    🔗 Керує обробкою запитів користувачів, делегуючи завдання відповідним методам.
    """

    def __init__(
        self,
        currency_manager: CurrencyManager,
        product_handler: ProductHandler,
        collection_handler: CollectionHandler,
        size_chart_handler: SizeChartHandlerBot,
        price_calculator: PriceCalculationHandler,
        availability_handler: AvailabilityHandler,
        search_resolver: IProductSearchProvider,
        url_parser_service: UrlParserService
    ):  
        self.currency_manager = currency_manager                                # 💱 Керування валютами
        self.product_handler = product_handler                                  # 🛍️ Обробка товарів
        self.collection_handler = collection_handler                            # 📚 Обробка колекцій
        self.size_chart_handler = size_chart_handler                            # 📏 Таблиці розмірів
        self.price_calculator = price_calculator                                # 🧮 Розрахунок цін
        self.availability_handler = availability_handler                        # 🌍 Мульти-регіональна наявність
        self.search_resolver = search_resolver                                  # 🔍 Розпізнавання товару
        self.url_parser_service = url_parser_service                            # 🔗 Визначення типу URL

        self.mode_handlers = {
            const.MODE_REGION_AVAILABILITY: self._handle_region_availability,   # 🌍 Наявність
            const.MODE_PRICE_CALCULATION: self._handle_price_calculation,       # 🧮 Ціна
            const.MODE_SIZE_CHART: self._handle_size_chart,                     # 📏 Таблиця
        }

    @error_handler
    async def handle_link(self, update: Update, context: CallbackContext):
        """
        📬 Головний метод-оркестратор. Визначає тип запиту і маршрутизує його.
        """
        if not update.message or not update.message.text:
            logger.warning("🚫 Немає повідомлення — ігноруємо оновлення")
            return

        text = update.message.text.strip()                                                  # 📤 Отриманий текст від користувача
        logger.debug(f"📥 Отримано повідомлення: {text}")
        await update.message.chat.send_action("typing")                                     # ✍️ Ефект "друкує"

        is_url = text.startswith("http")                                                    # 🔍 Перевірка на URL
        logger.debug(f"🔗 Це посилання: {is_url}")

        if not is_url:
            url_from_search = await self._handle_search_query(update, text)                 # 🔎 Виконуємо пошук
            if not url_from_search:
                return
            text = url_from_search                                                          # 🔁 Підставляємо знайдений URL

        was_routed_by_mode = await self._route_by_mode(update, context, url=text)           # 🎛️ Активний режим?
        if was_routed_by_mode:
            return

        await self._route_by_url_type(update, context, url=text)                            # 📡 Визначаємо тип URL

    async def _handle_search_query(self, update: Update, query: str) -> Optional[str]:
        """🔍 Обробляє текстовий пошуковий запит."""
        logger.debug(f"🔍 Пошуковий запит: {query}")
        if not is_valid_search_query(query):
            logger.warning(f"⚠️ Некоректний запит: {query}")
            await update.message.reply_text("⚠️ Введіть назву або артикул англійською.")
            return None

        await update.message.reply_text("🔍 Шукаю товар...")
        found_url = await self.search_resolver.resolve(query)                               # 🔗 Результат пошуку
        logger.debug(f"🔗 Результат пошуку: {found_url}")

        if not found_url:
            await update.message.reply_text("❌ Товар не знайдено.")
            return None

        return found_url

    async def _route_by_mode(self, update: Update, context: CallbackContext, url: str) -> bool:
        """🎛️ Маршрутизує запит відповідно до активного режиму користувача."""
        if context.user_data is None:
            return False
        
        mode = context.user_data.get("mode")									        # 🎛️ Отримуємо активний режим користувача (може бути: "availability", "price", "size")
        logger.debug(f"🎚️ Активний режим: {mode}")
        handler_method = self.mode_handlers.get(mode)						            # 🔎 Шукаємо відповідний обробник з мапи режимів

        if handler_method:
            logger.debug(f"➡️ Викликаємо обробник режиму: {handler_method.__name__}")
            await handler_method(update, context, url=url)				                # 🚀 Викликаємо відповідний метод обробки запиту
            return True																    # ✅ Повертаємо True, бо маршрут був знайдений і оброблений

        return False																	# ❌ Якщо режиму нема — повертаємо False

    async def _route_by_url_type(
            self, update: Update, context: CallbackContext, url: str
            ):
        
        """🧠 Визначає тип URL (товар чи колекція) і викликає відповідний обробник."""
        is_collection = self.url_parser_service.is_collection_url(url)				            # 📚 Перевіряємо: це колекція?
        is_product = self.url_parser_service.is_product_url(url)					            # 🛍️ Перевіряємо: це товар?
        logger.debug(f"🔎 is_collection={is_collection}, is_product={is_product}")

        if is_collection:
            logger.info(f"📚 Автоматично розпізнано колекцію: {url}")
            context.user_data.update({"mode": const.MODE_COLLECTION, "url": url})			    # 🧭 Зберігаємо режим у контексті
            await update.message.reply_text("📚 Виявлено колекцію. Обробляю...")				# 💬 Повідомляємо користувача
            await self.collection_handler.handle_collection(update, context)				    # 🔁 Викликаємо обробник колекцій

        elif is_product:
            logger.info(f"🛍️ Автоматично розпізнано товар: {url}")
            context.user_data["mode"] = const.MODE_PRODUCT							            # 🧭 Зберігаємо режим "товар"
            await update.message.reply_text("🔗 Виявлено товар. Обробляю...")				    # 💬 Повідомляємо користувача
            await self.product_handler.handle_url(update, context, url=url)				        # 🔁 Викликаємо обробник товару

        else:
            logger.warning(f"❓ Не вдалося розпізнати URL: {url}")
            await update.message.reply_text("❌ Це не схоже на посилання на товар або колекцію.")	# ⚠️ Помилка розпізнавання

    @product_url_required
    async def _handle_region_availability(
        self, update: Update, context: CallbackContext, url: str
        ):

        """🌍 Обробка в режимі мульти-регіональної перевірки."""
        logger.info(f"🌍 Запит перевірки наявності для: {url}")
        await update.message.reply_text("🌍 Виконую мульти-регіональну перевірку...")				# 💬 Повідомлення користувачу
        await self.availability_handler.handle_availability(update, context, url=url)				# 🧭 Викликаємо обробник наявності

    @product_url_required
    async def _handle_price_calculation(
        self, update: Update, context: CallbackContext, url: str
        ):

        """🧮 Обробка в режимі розрахунку ціни."""
        logger.info(f"🧮 Запит розрахунку ціни для: {url}")
        await update.message.reply_text("🧮 Виконую розрахунок ціни товару...")					    # 💬 Повідомлення користувачу
        await self.price_calculator.handle_price_calculation(update, context, url=url)				# 💵 Викликаємо сервіс розрахунку ціни

    @product_url_required
    async def _handle_size_chart(
        self, update: Update, context: CallbackContext, url: str
        ):

        """📏 Обробка в режимі генерації таблиці розмірів."""
        logger.info(f"📏 Запит таблиці розмірів для: {url}")
        await update.message.reply_text("📏 Генерую таблицю розмірів...")						# 💬 Повідомлення користувачу
        await self.size_chart_handler.size_chart_command(update, context, url=url)				# 📐 Викликаємо сервіс генерації таблиці