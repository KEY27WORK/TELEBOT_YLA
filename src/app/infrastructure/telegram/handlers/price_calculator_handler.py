# 📦 app/infrastructure/telegram/handlers/price_calculation_handler.py
"""
📦 price_calculation_handler.py — Обробник Telegram для розрахунку цiни.

✅ Клас `PriceCalculationHandler`:
    • Приймає посилання на товар
    • Завантажує товар через парсер
    • Створює PricingContext на основi валюти товару
    • Викликає доменний сервiс для розрахунку повної вартостi
    • Форматує результат i надсилає його у Telegram
"""

# 🌐 Внешние библиотеки
from telegram import Update
from telegram.ext import CallbackContext

# 🔠 Системні імпорти
import asyncio
import logging
from typing import Tuple, List

# 🧹 Внутрішні модулі проєкту
from app.errors.error_handler import error_handler
from app.domain.pricing.services import PricingService, FullPriceDetails, PricingContext
from app.domain.products.entities import ProductInfo
from app.infrastructure.currency.currency_converter import CurrencyConverter
from app.infrastructure.currency.currency_manager import CurrencyManager
from app.infrastructure.parsers.parser_factory import ParserFactory

# ================================
# 🏠 Обробник ціноутворення
# ================================
class PriceCalculationHandler:
    """
    🏠 Обробляє команду /price та рахує фінальну ціну товару.
    """

    def __init__(self, currency_manager: CurrencyManager, parser_factory: ParserFactory):
        """
        🔧 Ініціалізація з DI-залежностями.
        """
        self.currency_manager = currency_manager
        self.parser_factory = parser_factory
        self.pricing_service = PricingService()

        rates = self.currency_manager.get_all_rates()
        rates["UAH"] = 1.0
        self.converter = CurrencyConverter(rates)

    # ================================
    # 📢 ПУБЛІЧНИЙ ОБРОБНИК
    # ================================
    @error_handler
    async def handle_price_calculation(self, update: Update, context: CallbackContext, url: str):
        """
        📢 Головна точка входу: отримує URL i надсилає користувачу розрахунок.
        """
        _, message, _ = await self.calculate_and_format(url)
        await update.message.reply_text(message, parse_mode="HTML")

    # ================================
    # 🧠 ОСНОВНА ЛОГІКА РОЗРАХУНКУ
    # ================================
    async def calculate_and_format(self, url: str) -> Tuple[str, str, List[str]]:
        """
        🔧 Парсить товар, створює контекст, викликає сервіс, форматує.

        Returns:
            Tuple[str, str, List[str]]: Регіон, повідомлення, зображення
        """
        await self.currency_manager.update_all_rates()

        fresh_rates = self.currency_manager.get_all_rates()  
        fresh_rates["UAH"] = 1.0  # UAH завжди відносно себе = 1
        self.converter.rates = fresh_rates        

        parser = self.parser_factory.create_product_parser(url)
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не вдалося отримати дані про товар для: %s", url)
            return "Невідомо", "⚠️ Помилка при обробці!", []

        # 🌐 Контекст по валюті
        ctx = {
            "EUR": PricingContext(8.99, 1.0, "EUR", "germany"),
            "GBP": PricingContext(7.49, 1.0, "GBP", "uk"),
            "PLN": PricingContext(22.99, 1.0, "PLN", "poland")
        }.get(product_info.currency, PricingContext(6.99, 1.0, "USD", "us"))

        # 📊 Розрахунок
        details: FullPriceDetails = await asyncio.to_thread(
            self.pricing_service.calculate_full_price,
            price_in_base_currency=product_info.price,
            weight_lbs=product_info.weight,
            context=ctx,
            converter=self.converter
        )

        message = self._build_price_message(product_info, details, ctx)
        region = self._get_region_display(product_info.currency)
        images = [product_info.image_url]
        return region, message, images

    # ================================
    # 🔄 ФОРМУВАННЯ ПОВІДОМЛЕННЯ
    # ================================

    def _get_region_display(self, currency: str) -> str:
        """🌍 Повертає емодзі-регіон за валютою."""
        return {
            "USD": "🇺🇸 США",
            "EUR": "🇪🇺 Європа",
            "GBP": "🇬🇧 Велика Британія",
            "PLN": "🇵🇱 Польща"
        }.get(currency, "Невідомо")

    def _build_price_message(self, info: ProductInfo, details: FullPriceDetails, context: PricingContext) -> str:
        """🧾 Генерує повне повідомлення з усіма блоками."""
        parts = [
            self._build_header(info.title, info.image_url),
            self._build_price_block(details, info.currency),
            self._build_delivery_block(details, info.currency, context),
            self._build_cost_block(details, info.currency),
            self._build_markup_block(details),
            self._build_profit_block(details, info.currency),
        ]
        return "\n\n".join(parts)

    def _build_header(self, title: str, image_url: str) -> str:
        """🔗 Заголовок: назва товару + лiнк."""
        return (
            f"<b>🖼️ Зображення:</b> <a href='{image_url}'>Посилання</a>\n\n"
            f"<b>{title}:</b>"
        )

    def _get_currency_order_and_symbols(self, base_currency: str) -> Tuple[List[str], dict]:
        """💱 Порядок та символи валют для формату."""
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}
        order_map = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }
        return order_map.get(base_currency, ["usd", "eur", "uah"]), symbols

    def _format_prices(self, value_usd: float, currency_order: List[str], symbols: dict) -> str:
        """💸 Форматує цiни з USD у заданi валюти."""
        return " / ".join(
            f"{symbols[curr]}{self.converter.convert(value_usd, 'USD', curr):.2f}" for curr in currency_order
        )

    def _build_price_block(self, details: FullPriceDetails, currency: str) -> str:
        """💰 Блок: цiна продажу та округлення."""
        order, symbols = self._get_currency_order_and_symbols(currency)
        sale_prices = self._format_prices(details.sale_price_usd, order, symbols)
        rounded = self._format_prices(details.sale_price_rounded_usd, order, symbols)
        deltas = " / ".join(
            f"{symbols[c]}{self.converter.convert(details.round_delta_uah, 'UAH', c):.2f}" for c in order
        )
        return (
            f"\n<b>💵 Ціна продажу:</b> {sale_prices}\n"
            f"<u><b>💢 Округлена ціна:</b> {rounded}</u>\n"
            f"<b>🔁 % Округлення:</b> {deltas}"
        )

    def _build_delivery_block(self, details: FullPriceDetails, currency: str, context: PricingContext) -> str:
        """🚚 Блок доставки."""
        order, symbols = self._get_currency_order_and_symbols(currency)
        region_map = {"USD": "🇺🇸 США", "EUR": "🇪🇺 Європи", "GBP": "🇬🇧 Британії", "PLN": "🇵🇱 Польщі"}

        local_usd = self.converter.convert(context.local_delivery_cost, context.base_currency, "USD")
        local = self._format_prices(local_usd, order, symbols)
        meest = self._format_prices(details.full_delivery_usd - local_usd, order, symbols)
        total = self._format_prices(details.full_delivery_usd, order, symbols)

        return (
            f"\n<b>⚖️ Вага:</b> {details.weight_lbs:.2f} фунтів\n"
            f"<b>📦 Локальна доставка {region_map.get(currency, '')}:</b> {local}\n"
            f"<b>📦 Meest доставка:</b> {meest}\n"
            f"<b>🚚 Повна доставка в Україну з {region_map.get(currency, '')}:</b> {total}"
        )

    def _build_cost_block(self, details: FullPriceDetails, currency: str) -> str:
        """📊 Блок собівартості."""
        order, symbols = self._get_currency_order_and_symbols(currency)

        protection = self._format_prices(details.protection_usd, order, symbols)

        base = self._format_prices(details.cost_price_usd - details.full_delivery_usd, order, symbols)
        full = self._format_prices(details.cost_price_usd, order, symbols)
        return (
            f"<b>🛡️ Страховка Navidium:</b> {protection}\n"
            f"\n<b>🏷️ Собівартість без доставки:</b> {base}\n"
            f"<b>🏷️ Собівартість з доставкою:</b> {full}"
        )

    def _build_markup_block(self, details: FullPriceDetails) -> str:
        """📈 Блок накрутки.
        """
        return (
            f"\n<b>📉 % Коррекция процента накрутки:</b> {details.markup_adjustment:.2f}\n"
            f"<b>📈 % Процент накрутки:</b> {details.markup:.2f}"
        )

    def _build_profit_block(self, details: FullPriceDetails, currency: str) -> str:
        """💰 Блок прибутку."""
        order, symbols = self._get_currency_order_and_symbols(currency)
        raw = self._format_prices(details.profit_usd, order, symbols)
        rounded = self._format_prices(details.profit_rounded_usd, order, symbols)
        return (
            f"\n<b>📊 Чистий прибуток:</b> {raw}\n"
            f"<b>📊 Прибуток (з округленням):</b> {rounded}"
        )
