"""
💸 price_calculation_handler.py — итоговый обработчик расчета стоимости товара в Telegram-боте YoungLA Ukraine.

Работает на новой архитектуре: CurrencyConverter + ProductPriceService.
Полностью совместим с твоим текущим CurrencyManager.
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🔧 Бизнес-логика
from core.parsing.base_parser import BaseParser
from core.calculator.product_price_service import ProductPriceService
from core.calculator.currency_converter import CurrencyConverter
from core.currency.currency_manager import CurrencyManager

# 🛠️ Инфраструктура
from errors.error_handler import error_handler

# 📦 Модели данных
from models.product_info import ProductInfo

# 🧱 Системные
import logging


class PriceCalculationHandler:
    def __init__(self, currency_manager: CurrencyManager):
        self.currency_manager = currency_manager

    @error_handler
    async def handle_price_calculation(self, update: Update, context: CallbackContext, url: str):
        self.currency_manager.update_rate()
        rates = self.currency_manager.get_all_rates()
        rates["UAH"] = 1.0  # ✅ фикс на UAH

        currency_converter = CurrencyConverter(rates)
        price_service = ProductPriceService(currency_converter)

        parser = BaseParser(url)
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не удалось получить полные данные о товаре")
            return

        pricing = price_service.calculate(product_info.price, product_info.weight, product_info.currency)

        message = self._build_price_message(product_info.title, pricing, product_info.weight, product_info.image_url, product_info.currency)
        await update.message.reply_text(message, parse_mode="HTML")

    async def calculate_and_format(self, url: str) -> tuple:
        self.currency_manager.update_rate()
        rates = self.currency_manager.get_all_rates()
        rates["UAH"] = 1.0  # ✅ фикс на UAH

        currency_converter = CurrencyConverter(rates)
        price_service = ProductPriceService(currency_converter)

        parser = BaseParser(url)
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не удалось получить полные данные о товаре")
            return "Невідомо", "⚠️ Помилка при обробці товару!", []

        pricing = price_service.calculate(product_info.price, product_info.weight, product_info.currency)

        message = self._build_price_message(product_info.title, pricing, product_info.weight, product_info.image_url, product_info.currency)
        region = self._get_region_display(product_info.currency)

        return region, message, product_info.images

    @staticmethod
    def _get_region_display(currency: str) -> str:
        return {
            "USD": "🇺🇸 США",
            "EUR": "🇪🇺 Європа",
            "GBP": "🇬🇧 Велика Британія",
            "PLN": "🇵🇱 Польща"
        }.get(currency, "Невідомо")

    def _build_price_message(self, title: str, p: dict, weight: float, image_url: str, currency: str) -> str:
        lines = [
            f"<b>🖼️ Зображення:</b> <a href='{image_url}'>Посилання</a>\n\n<b>{title}:</b>",
            self._build_price_block(p, currency),
            self._build_delivery_block(p, currency),
            self._build_cost_block(p, currency),
            self._build_markup_block(p),
            self._build_profit_block(p, currency),
        ]
        return "\n".join(lines)

    # === Сборка каждого текстового блока ===

    def _build_price_block(self, p: dict, currency: str) -> str:
        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}

        sale_prices = " / ".join(f"{symbols[cur]}{p[f'sale_price_{cur}']:.2f}" for cur in currency_order)
        sale_prices_rounded = " / ".join(f"{symbols[cur]}{p[f'sale_price_rounded_{cur}']:.2f}" for cur in currency_order)
        rounds = " / ".join(f"{symbols[cur]}{p[f'round_{cur}']:.2f}" for cur in currency_order)

        return (
            f"\n<b>💵 Ціна продажу:</b> {sale_prices}\n"
            f"<u><b>💢 Округлена ціна:</b> {sale_prices_rounded}</u>\n"
            f"<b>🔁 % Округлення:</b> {rounds}"
        )

    def _build_delivery_block(self, p: dict, currency: str) -> str:
        region_map = {"USD": "🇺🇸 США", "EUR": "🇪🇺 Європи", "GBP": "🇬🇧 Британії", "PLN": "🇵🇱 Польщі"}
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}

        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

        local_key = {"USD": "us_delivery", "GBP": "uk_delivery", "EUR": "eu_delivery", "PLN": "pl_delivery"}[currency]

        local_delivery = " / ".join(f"{symbols[cur]}{p[f'{local_key}_{cur}']:.2f}" for cur in currency_order)
        meest_delivery = " / ".join(f"{symbols[cur]}{p[f'meest_delivery_{cur}']:.2f}" for cur in currency_order)
        total_delivery = " / ".join(f"{symbols[cur]}{p[f'delivery_price_{cur}']:.2f}" for cur in currency_order)

        return (
            f"\n<b>⚖️ Вага:</b> {p['weight_lbs']:.2f} фунтів\n"
            f"<b>📦 Локальна доставка {region_map.get(currency, '')}:</b> {local_delivery}\n"
            f"<b>📦 Meest доставка:</b> {meest_delivery}\n"
            f"<b>🚚 Повна доставка в Україну з {region_map.get(currency, '')}:</b> {total_delivery}"
        )

    def _build_cost_block(self, p: dict, currency: str) -> str:
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}

        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

        cost_without_delivery = " / ".join(f"{symbols[cur]}{p[f'cost_price_without_delivery_{cur}']:.2f}" for cur in currency_order)
        cost_with_delivery = " / ".join(f"{symbols[cur]}{p[f'cost_price_{cur}']:.2f}" for cur in currency_order)

        return (
            f"\n<b>🏷️ Собівартість без доставки:</b> {cost_without_delivery}\n"
            f"<b>🏷️ Собівартість з доставкою:</b> {cost_with_delivery}"
        )

    def _build_markup_block(self, p: dict) -> str:
        return (
            f"\n<b>📉 % Коррекция процента накрутки:</b> {p['markup_adjustment']:.2f}\n"
            f"<b>📈 % Процент накрутки:</b> {p['markup']:.2f}"
        )

    def _build_profit_block(self, p: dict, currency: str) -> str:
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}

        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

        profit = " / ".join(f"{symbols[cur]}{p[f'profit_{cur}']:.2f}" for cur in currency_order)
        profit_rounded = " / ".join(f"{symbols[cur]}{p[f'profit_with_round_{cur}']:.2f}" for cur in currency_order)

        return (
            f"\n<b>📊 Чистий прибуток:</b> {profit}\n"
            f"<b>📊 Прибуток (з округленням):</b> {profit_rounded}"
        )
