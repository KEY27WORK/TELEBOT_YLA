"""
💸 price_calculation_handler.py — модуль для обробки вартості товару в Telegram-боті YoungLA Ukraine.

🔹 Клас:
- `PriceCalculationHandler` — розрахунок ціни, доставки, націнки та прибутку по товару.

Використовує:
- Парсер товару (ProductParser)
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
    🤖 Обработчик расчета стоимости товара по ссылке.
    Используется в Telegram-боте для парсинга ссылки, расчета цены и формирования сообщения с деталями.
    """

    def __init__(self, currency_manager: CurrencyManager):
        self.currency_manager = currency_manager  # 💱 Объект для получения и обновления курсов валют
        self.price_factory = PriceCalculatorFactory(currency_manager)  # 🏭 Фабрика для получения нужного калькулятора

    @error_handler
    async def handle_price_calculation(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основной метод — принимает ссылку, парсит товар, считает цену, отправляет сообщение.
        """
        self.currency_manager.update_rate()  # 🔄 Оновлюємо актуальні курси валют
        parser = BaseParser(url)  # 🌐 Получаем парсер по ссылке
        product_info = await parser.get_product_info()  # 🛍️ Парсимо інформацію про товар

        if not product_info:
            await update.message.reply_text("⚠️ Не вдалося отримати інформацію про товар.")
            return

        title, price, _, image_url, weight, _, _, currency = product_info  # 📋 Розпаковуємо інформацію про товар
        calculator = self.price_factory.get_calculator(currency)  # 🛠️ Вибираємо калькулятор по валюті
        pricing = await asyncio.to_thread(calculator.calculate, price, weight, currency)  # 📈 Виконуємо розрахунок ціни в окремому потоці

        message = self._build_price_message(title, pricing, weight, image_url, currency)  # 📦 Формуємо фінальне повідомлення
        await update.message.reply_text(message, parse_mode="HTML")  # ✉️ Надсилаємо повідомлення користувачу

    async def calculate_and_format(self, url: str) -> tuple:
            """
            🔧 Публичный метод: получает ссылку, парсит товар, рассчитывает цену и возвращает:
            - Регион сайта (с флагом)
            - Готовое сообщение о цене
            - Список изображений товара
            """
            self.currency_manager.update_rate()  # 🔄 Обновляем курс валют
            parser = BaseParser(url)  # 🌐 Создаем парсер
            product_info = await parser.get_product_info()  # 📦 Получаем данные о товаре

            if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
                logging.error("❌ Не удалось получить полные данные о товаре")
                return "Невідомо", "⚠️ Помилка при обробці товару!", []

            title = product_info.title
            price = product_info.price
            image_url = product_info.image_url
            weight = product_info.weight
            images = product_info.images
            currency = product_info.currency
            
            calculator = self.price_factory.get_calculator(currency)  # 🧮 Калькулятор для валюты
            pricing = await asyncio.to_thread(calculator.calculate, price, weight, currency)  # 📈 Расчет в потоке

            message = self._build_price_message(title, pricing, weight, image_url, currency)  # 🧩 Готовим сообщение
            region = self._get_region_display(currency)  # 🌍 Регіон з прапором

            return region, message, images
        
    @staticmethod
    def _get_region_display(currency: str) -> str:
            """🌍 Возвращает регион с флагом по валюте."""
            return {
                "USD": "🇺🇸 США",
                "EUR": "🇪🇺 Європа",
                "GBP": "🇬🇧 Велика Британія",
                "PLN": "🇵🇱 Польща"
            }.get(currency, "Невідомо")


    def _build_price_message(self, title: str, pricing: dict, weight: float, image_url: str, currency: str) -> str:
        """
        🧩 Формуємо повідомлення із блоків (заголовок, ціна, доставка, собівартість, націнка, прибуток).
        """
        lines = [
            self._build_header(title, image_url),  # 🖼️ Заголовок та посилання на фото
            self._build_price_block(pricing, currency),  # 💵 Блок ціни
            self._build_delivery_block(pricing, currency),  # 🚚 Блок доставки
            self._build_cost_block(pricing, currency),  # 🏷️ Блок собівартості
            self._build_markup_block(pricing),  # 📊 Блок накрутки
            self._build_profit_block(pricing, currency),  # 💰 Блок прибутку
        ]
        return "\n".join(lines)  # 🧾 Складаємо всі частини в одне повідомлення

    def _build_header(self, title: str, image_url: str) -> str:
        """🔠 Блок с заголовком и ссылкой на изображение товара."""
        return (
            f"<b>🖼️ Зображення:</b> <a href='{image_url}'>Посилання</a>\n\n"
            f"<b>{title}:</b>"
        )

    def _build_price_block(self, p: dict, currency: str) -> str:
        """💸 Блок з ціною продажу та округленням залежно від регіону."""
        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])  # 🔄 Порядок валют за регіоном

        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"} # 💱 Символи валют

        sale_prices = " / ".join(
            [f"{symbols[cur]}{p[f'sale_price_{cur}']:.2f}" for cur in currency_order] 
        )
        sale_prices_rounded = " / ".join(
            [f"{symbols[cur]}{p[f'sale_price_rounded_{cur}']:.2f}" for cur in currency_order]
        )
        rounds = " / ".join(
            [f"{symbols[cur]}{p[f'round_{cur}']:.2f}" for cur in currency_order]
        )

        return (
            f"\n<b>💵 Ціна продажу:</b> {sale_prices}\n"
            f"<u><b>💢 Округлена ціна:</b> {sale_prices_rounded}</u>\n"
            f"<b>🔁 % Округлення:</b> {rounds}"
        )
   
    def _build_currency_rates_block(self, p: dict, currency: str) -> str:
        rates = [f"\n<b>💱 Курси валют:</b>"]
        rates.append(f"💲 USD → UAH: {p['usd_rate']:.2f}")

        if currency in ("GBP", "EUR", "PLN"):
            rates.append(f"{currency} → UAH: {p[currency.lower() + '_rate']:.2f}")
            rates.append(f"{currency} → USD: {p[currency.lower() + '_to_usd']:.4f}")

        if currency == "PLN":
            rates.append(f"PLN → EUR: {p['pln_to_eur']:.4f}")
            rates.append(f"EUR → USD: {p['eur_to_usd']:.4f}")

        return "\n".join(rates)

    def _build_delivery_block(self, p: dict, currency: str) -> str:
        """🚚 Блок доставки з цінами у всіх валютах."""
        region_map = {"USD": "🇺🇸 США", "EUR": "🇪🇺 Європи", "GBP": "🇬🇧 Британії", "PLN": "🇵🇱 Польщі"}
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}

        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

        # 🚚 Локальна доставка
        local_key = {"USD": "us_delivery", "GBP": "uk_delivery", "EUR": "eu_delivery", "PLN": "pl_delivery"}[currency]  # 🔄 Локальна доставка за країною
        local_delivery = " / ".join(
            f"{symbols[cur]}{p[f'{local_key}_{cur}']:.2f}" for cur in currency_order
        )

        # Meest доставка
        meest_delivery = " / ".join(
            f"{symbols[cur]}{p[f'meest_delivery_{cur}']:.2f}" for cur in currency_order
        )

        # Повна доставка
        total_delivery = " / ".join(
            f"{symbols[cur]}{p[f'delivery_price_{cur}']:.2f}" for cur in currency_order
        )

        return (
            f"\n<b>⚖️ Вага:</b> {p['weight_lbs']:.2f} фунтів\n"
            f"<b>📦 Локальна доставка {region_map.get(currency, '')}:</b> {local_delivery}\n"
            f"<b>📦 Meest доставка:</b> {meest_delivery}\n"
            f"<b>🚚 Повна доставка в Україну з {region_map.get(currency, '')}:</b> {total_delivery}"
        )

    def _build_cost_block(self, p: dict, currency: str) -> str:
        """📊 Блок собівартості (з доставкою та без)."""
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}
        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])
    
        cost_without_delivery = " / ".join(
            f"{symbols[cur]}{p[f'cost_price_without_delivery_{cur}']:.2f}" for cur in currency_order
        )
        cost_with_delivery = " / ".join(
            f"{symbols[cur]}{p[f'cost_price_{cur}']:.2f}" for cur in currency_order
        )
    
        return (
            f"\n<b>🏷️ Собівартість без доставки:</b> {cost_without_delivery}\n"
            f"<b>🏷️ Собівартість з доставкою:</b> {cost_with_delivery}"
        )

    def _build_markup_block(self, p: dict) -> str:
        """📈 Блок с процентом наценки и коррекцией на доставку."""
        return (
            f"\n<b>📉 % Коррекция процента накрутки:</b> {p['markup_adjustment']:.2f}\n"
            f"<b>📈 % Процент накрутки:</b> {p['markup']:.2f}"
        )

    def _build_profit_block(self, p: dict, currency: str) -> str:
        """📈 Блок прибутку до та після округлення."""
        symbols = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}
        currency_order = {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

        profit = " / ".join(
            f"{symbols[cur]}{p[f'profit_{cur}']:.2f}" for cur in currency_order
        )
        profit_rounded = " / ".join(
            f"{symbols[cur]}{p[f'profit_with_round_{cur}']:.2f}" for cur in currency_order
        )

        return (
            f"\n<b>📊 Чистий прибуток:</b> {profit}\n"
            f"<b>📊 Прибуток (з округленням):</b> {profit_rounded}"
        ) 
  