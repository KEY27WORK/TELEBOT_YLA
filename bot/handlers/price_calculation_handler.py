"""
💸 price_calculation_handler.py — модуль для обробки вартості товару в Telegram-боті YoungLA Ukraine.

🔹 Клас:
- `PriceCalculationHandler` — розрахунок ціни, доставки, націнки та прибутку по товару.

Використовує:
- Парсер товару (BaseParser)
- Калькулятор по валюті (PriceCalculatorFactory)
- Менеджер курсів валют (CurrencyManager)
- Telegram API для відправки повідомлень
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🔧 Бізнес-логіка
from core.parsing.base_parser import BaseParser
from core.calculator.calculator import PriceCalculatorFactory
from core.currency.currency_manager import CurrencyManager

# 🛠️ Інфраструктура
from errors.error_handler import error_handler

# 📦 Моделі даних
from models.product_info import ProductInfo

# 🧱 Системні
import logging
import asyncio


class PriceCalculationHandler:
    """
    💸 Основний обробник для розрахунку ціни, доставки та прибутку по товару.

    Використовується:
    - Для ручного розрахунку вартості по посиланню
    - Для обробки парсинг-результатів у Telegram-боті
    """

    def __init__(self, currency_manager: CurrencyManager):
        """
        Ініціалізація обробника з валютою та калькулятором.
        """
        self.currency_manager = currency_manager
        self.price_factory = PriceCalculatorFactory(currency_manager)

    @error_handler
    async def handle_price_calculation(self, update: Update, context: CallbackContext, url: str):
        """
        📥 Основний обробник команди в Telegram — парсить URL, рахує ціну, відправляє результат.
        """
        self.currency_manager.update_rate()
        parser = BaseParser(url)
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не удалось получить полные данные о товаре")
            return

        title, price, image_url, weight, currency = (
            product_info.title,
            product_info.price,
            product_info.image_url,
            product_info.weight,
            product_info.currency
        )

        calculator = self.price_factory.get_calculator(currency)
        pricing = await asyncio.to_thread(calculator.calculate, price, weight, currency)

        message = self._build_price_message(title, pricing, weight, image_url, currency)
        await update.message.reply_text(message, parse_mode="HTML")

    async def calculate_and_format(self, url: str) -> tuple:
        """
        🔧 Публічний метод: повертає фінальний текст повідомлення для інтеграції в ProductHandler.

        :return: (регіон, повідомлення, список зображень)
        """
        self.currency_manager.update_rate()
        parser = BaseParser(url)
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не удалось получить полные данные о товаре")
            return "Невідомо", "⚠️ Помилка при обробці товару!", []

        title = product_info.title
        price = product_info.price
        image_url = product_info.image_url
        weight = product_info.weight
        images = product_info.images
        currency = product_info.currency

        calculator = self.price_factory.get_calculator(currency)
        pricing = await asyncio.to_thread(calculator.calculate, price, weight, currency)

        message = self._build_price_message(title, pricing, weight, image_url, currency)
        region = self._get_region_display(currency)

        return region, message, images

    @staticmethod
    def _get_region_display(currency: str) -> str:
        """🌎 Повертає емодзі-регіон за валютою."""
        return {
            "USD": "🇺🇸 США",
            "EUR": "🇪🇺 Європа",
            "GBP": "🇬🇧 Велика Британія",
            "PLN": "🇵🇱 Польща"
        }.get(currency, "Невідомо")

    def _build_price_message(self, title: str, pricing: dict, weight: float, image_url: str, currency: str) -> str:
        """
        📝 Збирає фінальне повідомлення по ціні з усіх блоків.
        """
        lines = [
            self._build_header(title, image_url),
            self._build_price_block(pricing, currency),
            self._build_delivery_block(pricing, currency),
            self._build_cost_block(pricing, currency),
            self._build_markup_block(pricing),
            self._build_profit_block(pricing, currency),
        ]
        return "\n".join(lines)

    def _build_header(self, title: str, image_url: str) -> str:
        """🔗 Заголовок з посиланням на фото товару."""
        return (
            f"<b>🖼️ Зображення:</b> <a href='{image_url}'>Посилання</a>\n\n"
            f"<b>{title}:</b>"
        )

    def _build_price_block(self, p: dict, currency: str) -> str:
        """💰 Блок з базовими цінами продажу."""
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
        """🚚 Блок доставки (локальна, Meest, загальна)."""
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
        """📊 Блок собівартості товару."""
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
        """📈 Блок накрутки (процент накрутки та корекція)."""
        return (
            f"\n<b>📉 % Коррекция процента накрутки:</b> {p['markup_adjustment']:.2f}\n"
            f"<b>📈 % Процент накрутки:</b> {p['markup']:.2f}"
        )

    def _build_profit_block(self, p: dict, currency: str) -> str:
        """💰 Чистий прибуток до та після округлення."""
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
