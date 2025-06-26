"""🔗 link_handler.py — обробка текстових посилань у Telegram-боті YoungLA Ukraine."""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🤖 Обробники
from bot.handlers.size_chart_handler import SizeChartHandlerBot
from bot.handlers.price_calculation_handler import PriceCalculationHandler

# 🛍️ Обробка товарів та колекцій (нова структура)
from bot.handlers.product.product_handler import ProductHandler
from bot.handlers.product.collection_handler import CollectionHandler

from core.product_availability.availability_handler import AvailabilityHandler

# 🧠 Сервіси та інфраструктура
from core.currency.currency_manager import CurrencyManager
from errors.error_handler import error_handler

# 🧱 Системні
import re
from typing import Dict, Any


class LinkHandler:
    """🔗 Обробник посилань: визначає тип посилання та перенаправляє у відповідний режим."""

    def __init__(
        self,
        currency_manager: CurrencyManager,
        product_handler: ProductHandler,
        collection_handler: CollectionHandler,
        size_chart_handler: SizeChartHandlerBot,
        price_calculator: PriceCalculationHandler,
        availability_handler: AvailabilityHandler
    ):
        self.currency_manager = currency_manager
        self.product_handler = product_handler
        self.collection_handler = collection_handler
        self.size_chart_handler = size_chart_handler
        self.price_calculator = price_calculator
        self.availability_handler = availability_handler

    @error_handler
    async def handle_link(self, update: Update, context: CallbackContext):
        """📬 Аналізує отриманий текст та викликає відповідний підрежим обробки."""
        user_data: Dict[str, Any] = context.user_data
        text = update.message.text.strip()
        mode = user_data.get("mode")

        # 🔍 Визначаємо тип посилання за шаблоном
        is_collection = bool(re.match(r"https?://(?:www|eu|uk)\.youngla\.com/collections/", text))
        is_product = bool(re.match(r"https?://(?:www|eu|uk)\.youngla\.com/products/", text))

        # --- 🌍 Режим мульти-регіональної перевірки ---
        if mode == "region_availability":
            if is_product:
                await update.message.reply_text("🌍 Виконую мульти-регіональну перевірку...")
                await self.availability_handler.handle_availability(update, context, text)
            elif is_collection:
                await update.message.reply_text("📚 Це посилання на колекцію. Перемикаю режим на колекції.")
                user_data["mode"] = "collection"
                await self.collection_handler.handle_collection(update, context)
            else:
                await update.message.reply_text("❌ Це не посилання на товар. Перевір, будь ласка.")
            return

        # --- 🧮 Режим розрахунку ціни ---
        if mode == "price_calculation":
            if is_product:
                await update.message.reply_text("🧮 Виконую розрахунок ціни товару...")
                await self.price_calculator.handle_price_calculation(update, context, text)
            elif is_collection:
                await update.message.reply_text("📚 Це посилання на колекцію. Перемикаю режим на колекції.")
                user_data["mode"] = "collection"
                await self.collection_handler.handle_collection(update, context)
            else:
                await update.message.reply_text("❌ Це не посилання на товар. Перевір, будь ласка.")
            return

        # --- 📏 Режим таблиці розмірів ---
        if mode == "size_chart":
            if is_collection:
                await update.message.reply_text("📚 Виявлено колекцію. Вимикаю режим таблиць, перемикаюсь на колекції.")
                user_data["mode"] = "collection"
                await self.collection_handler.handle_collection(update, context)
            elif is_product:
                await update.message.reply_text("📏 Генерую таблицю розмірів...")
                await self.size_chart_handler.size_chart_command(update, context, url=text)
            else:
                await update.message.reply_text("❌ Це не схоже на посилання на товар. Перевір, будь ласка.")
            return

        # --- 🤖 Автоматичне визначення режиму ---
        if is_collection:
            if mode != "collection":
                user_data["mode"] = "collection"
                await update.message.reply_text("📚 Перемикаю режим на колекції.")
            await self.collection_handler.handle_collection(update, context)

        elif is_product:
            if mode != "product":
                user_data["mode"] = "product"
                await update.message.reply_text("🔗 Перемикаю режим на окремі товари.")
            await self.product_handler.handle_url(update, context)

        else:
            await update.message.reply_text("❌ Це не схоже на посилання на товар або колекцію. Перевір, будь ласка.")
