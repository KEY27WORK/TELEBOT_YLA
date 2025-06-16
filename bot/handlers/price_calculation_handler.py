'''
💸 price_calculation_handler.py — обробник розрахунку вартості товару в Telegram-боті YoungLA Ukraine.

🔹 Особливості:
- Використовує нову архітектуру CurrencyConverter + ProductPriceService
- Відповідає принципам SOLID та чистої архітектури
- Структуровані блоки генерації повідомлень
'''

# 📚 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🛠️ Базова бізнес-логіка
from core.parsing.base_parser import BaseParser
from core.calculator.product_price_service import ProductPriceService
from core.calculator.currency_converter import CurrencyConverter
from core.currency.currency_manager import CurrencyManager

# ⚠️ Обробка помилок
from errors.error_handler import error_handler

# 📦 Моделі даних
from models.product_info import ProductInfo

# 🧱 Системні модулі
import logging


class PriceCalculationHandler:
    '''
    📦 Основний обробник для розрахунку та форматування фінальної ціни товару.
    '''

    # === 🔧 Константи ===
    SYMBOLS = {"usd": "$", "eur": "€", "uah": "₴", "gbp": "£", "pln": "zł"}
    REGION_MAP = {"USD": "🇺🇸 США", "EUR": "🇪🇺 Європа", "GBP": "🇬🇧 Британія", "PLN": "🇵🇱 Польща"}
    LOCAL_DELIVERY_KEYS = {"USD": "us_delivery", "GBP": "uk_delivery", "EUR": "eu_delivery", "PLN": "pl_delivery"}

    def __init__(self, currency_manager: CurrencyManager):
        '''
        🔧 Ініціалізація обробника розрахунку цін.

        :param currency_manager: Менеджер валютних курсів (CurrencyManager)
        '''
        self.currency_manager = currency_manager

    @error_handler
    async def handle_price_calculation(self, update: Update, context: CallbackContext, url: str):
        '''
        🚀 Обробляє основний запит від користувача Telegram.

        - Отримує курс валют.
        - Парсить продукт.
        - Розраховує ціну.
        - Формує повідомлення.
        - Відправляє готовий текст у чат.
        '''
        pricing, product_info = await self._get_pricing(url)
        if pricing is None:
            return
        message = self._build_price_message(product_info.title, pricing, product_info.weight, product_info.image_url, product_info.currency)
        await update.message.reply_text(message, parse_mode="HTML")

    async def calculate_and_format(self, url: str) -> tuple:
        '''
        📦 Внутрішній виклик для інших частин бота.

        - Повертає: регіон, сформоване повідомлення, список фото.
        - Використовується для inline-запитів та тестів.
        '''
        pricing, product_info = await self._get_pricing(url)
        if pricing is None:
            return "Невідомо", "⚠️ Помилка при обробці товару!", []
        message = self._build_price_message(product_info.title, pricing, product_info.weight, product_info.image_url, product_info.currency)
        region = self.REGION_MAP.get(product_info.currency, "Невідомо")
        return region, message, product_info.images

    async def _get_pricing(self, url: str):
        '''
        🔄 Внутрішній метод для отримання повного об'єкту ціни.

        - Оновлює курси валют.
        - Ініціалізує конвертер валют.
        - Парсить інформацію по продукту.
        - Розраховує фінальну ціну.

        :return: pricing dict та product_info
        '''
        self.currency_manager.update_rate()
        rates = self.currency_manager.get_all_rates()
        rates["UAH"] = 1.0  # ✅ завжди фіксуємо UAH

        currency_converter = CurrencyConverter(rates)
        price_service = ProductPriceService(currency_converter)

        parser = BaseParser(url)
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не вдалося отримати дані про товар")
            return None, None

        pricing = price_service.calculate(product_info.price, product_info.weight, product_info.currency)
        return pricing, product_info


    # === 🔧 Генерація текстових блоків ===

    def _build_price_message(self, title: str, p: dict, weight: float, image_url: str, currency: str) -> str:
        '''
        🧾 Збірка повного повідомлення з розрахунками.

        Формує фінальне повідомлення, яке містить:
        - Зображення з посиланням
        - Назву товару
        - Ціни (базові та округлені)
        - Вартість доставки
        - Собівартість
        - Накрутку
        - Прибуток
        '''
        
        # Збираємо усі блоки повідомлення по секціях
        lines = [
            f"<b>🖼️ Зображення:</b> <a href='{image_url}'>Посилання</a>\n\n<b>{title}:</b>",
            self._build_price_block(p, currency),
            self._build_delivery_block(p, currency),
            self._build_cost_block(p, currency),
            self._build_markup_block(p),
            self._build_profit_block(p, currency),
        ]
        return "\n".join(lines)

    def _get_currency_order(self, currency: str) -> list:
        '''
        📊 Порядок валют для виводу згідно регіону.
        
        Дає змогу задавати, у якому порядку виводити валюти для кожної країни.
        '''
        return {
            "USD": ["usd", "eur", "uah"],
            "EUR": ["eur", "usd", "uah"],
            "GBP": ["gbp", "usd", "eur", "uah"],
            "PLN": ["pln", "usd", "eur", "uah"]
        }.get(currency, ["usd", "eur", "uah"])

    def _build_price_block(self, p: dict, currency: str) -> str:
        '''
        💰 Блок цін та округлення.

        Виводить:
        - Ціни продажу
        - Округлені ціни
        - Суму округлення
        '''
        
        currency_order = self._get_currency_order(currency)

        # Формуємо блоки для базової ціни
        sale_prices = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'sale_price_{cur}']:.2f}" for cur in currency_order
        )

        # Формуємо блоки для округленої ціни
        sale_prices_rounded = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'sale_price_rounded_{cur}']:.2f}" for cur in currency_order
        )

        # Формуємо блок різниці округлення
        rounds = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'round_{cur}']:.2f}" for cur in currency_order
        )

        # Повертаємо фінальний блок тексту
        return (
            f"\n<b>💵 Ціна продажу:</b> {sale_prices}\n"
            f"<u><b>💢 Округлена ціна:</b> {sale_prices_rounded}</u>\n"
            f"<b>🔁 % Округлення:</b> {rounds}"
        )

    def _build_cost_block(self, p: dict, currency: str) -> str:
        '''
        🏷️ Блок собівартості.

        Формує текстовий блок із собівартістю товару:
        - без урахування доставки
        - з урахуванням доставки
        Для кожної валюти відображає значення у відповідному порядку.
        '''

        currency_order = self._get_currency_order(currency)

        cost_without_delivery = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'cost_price_without_delivery_{cur}']:.2f}" for cur in currency_order
        )

        cost_with_delivery = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'cost_price_{cur}']:.2f}" for cur in currency_order
        )

        return (
            f"\n<b>🏷️ Собівартість без доставки:</b> {cost_without_delivery}\n"
            f"<b>🏷️ Собівартість з доставкою:</b> {cost_with_delivery}"
        )

    def _build_markup_block(self, p: dict) -> str:
        '''
        📈 Блок накруток.

        Формує текстовий блок з інформацією:
        - базова накрутка
        - корекція накрутки на основі доставки
        '''
        return (
            f"\n<b>📉 % Коррекция процента накрутки:</b> {p['markup_adjustment']:.2f}\n"
            f"<b>📈 % Процент накрутки:</b> {p['markup']:.2f}"
        )

    def _build_profit_block(self, p: dict, currency: str) -> str:
        '''
        📊 Блок прибутків.

        Формує текстовий блок з:
        - чистим прибутком до округлення
        - прибутком після округлення
        Всі значення відображаються по відповідних валютах.
        '''

        currency_order = self._get_currency_order(currency)

        profit = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'profit_{cur}']:.2f}" for cur in currency_order
        )

        profit_rounded = " / ".join(
            f"{self.SYMBOLS[cur]}{p[f'profit_with_round_{cur}']:.2f}" for cur in currency_order
        )

        return (
            f"\n<b>📊 Чистий прибуток:</b> {profit}\n"
            f"<b>📊 Прибуток (з округленням):</b> {profit_rounded}"
        )


    def _build_delivery_block(self, p: dict, currency: str) -> str:
            '''
            🚚 Блок розрахунку доставки.

            Формує текстовий блок із деталями доставки для відображення у Telegram.
            Включає:
            - Локальну доставку по країні
            - Доставку Meest
            - Повну сумарну доставку до України
            - Відображення ваги товару
            '''

            # Отримуємо порядок валют, в якому потрібно відображати суми (для кожної валюти різний пріоритет)
            currency_order = self._get_currency_order(currency)

            # Визначаємо ключ локальної доставки в словнику результатів (відповідно до валюти)
            local_key = self.LOCAL_DELIVERY_KEYS[currency]

            # 🔢 Формуємо рядок локальної доставки для кожної валюти
            local_delivery = " / ".join(
                f"{self.SYMBOLS[cur]}{p[f'{local_key}_{cur}']:.2f}" for cur in currency_order
            )

            # 🔢 Формуємо рядок доставки Meest для кожної валюти
            meest_delivery = " / ".join(
                f"{self.SYMBOLS[cur]}{p[f'meest_delivery_{cur}']:.2f}" for cur in currency_order
            )

            # 🔢 Формуємо сумарну доставку (локальна + Meest) для кожної валюти
            total_delivery = " / ".join(
                f"{self.SYMBOLS[cur]}{p[f'delivery_price_{cur}']:.2f}" for cur in currency_order
            )

            # 📝 Збираємо фінальний блок тексту для Telegram
            return (
                f"\n<b>⚖️ Вага:</b> {p['weight_lbs']:.2f} фунтів\n"
                f"<b>📦 Локальна доставка {self.REGION_MAP.get(currency, '')}:</b> {local_delivery}\n"
                f"<b>📦 Meest доставка:</b> {meest_delivery}\n"
                f"<b>🚚 Повна доставка в Україну з {self.REGION_MAP.get(currency, '')}:</b> {total_delivery}"
            ) 
 
    def _build_cost_block(self, p: dict, currency: str) -> str:
         '''
         🏷️ Блок собівартості.
 
         Формує текстовий блок із собівартістю товару:
         - без урахування доставки
         - з урахуванням доставки
         Для кожної валюти відображає значення у відповідному порядку.
         '''
 
         # Визначаємо порядок відображення валют для даної валюти
         currency_order = self._get_currency_order(currency)
 
         # Формуємо рядок собівартості без доставки для кожної валюти
         cost_without_delivery = " / ".join(
             f"{self.SYMBOLS[cur]}{p[f'cost_price_without_delivery_{cur}']:.2f}" for cur in currency_order
         )
 
         # Формуємо рядок собівартості з доставкою для кожної валюти
         cost_with_delivery = " / ".join(
             f"{self.SYMBOLS[cur]}{p[f'cost_price_{cur}']:.2f}" for cur in currency_order
         )
 
         # Повертаємо фінальний блок тексту
         return (
             f"\n<b>🏷️ Собівартість без доставки:</b> {cost_without_delivery}\n"
             f"<b>🏷️ Собівартість з доставкою:</b> {cost_with_delivery}"
         )
 
    def _build_markup_block(self, p: dict) -> str:
         '''
         📈 Блок накруток.
 
         Формує текстовий блок з інформацією:
         - базова накрутка
         - корекція накрутки на основі доставки
         '''
         return (
             f"\n<b>📉 % Коррекция процента накрутки:</b> {p['markup_adjustment']:.2f}\n"
             f"<b>📈 % Процент накрутки:</b> {p['markup']:.2f}"
         )
 
    def _build_profit_block(self, p: dict, currency: str) -> str:
         '''
         📊 Блок прибутків.
 
         Формує текстовий блок з:
         - чистим прибутком до округлення
         - прибутком після округлення
         Всі значення відображаються по відповідних валютах.
         '''
 
         # Визначаємо порядок валют
         currency_order = self._get_currency_order(currency)
 
         # Формуємо чистий прибуток без округлення
         profit = " / ".join(
             f"{self.SYMBOLS[cur]}{p[f'profit_{cur}']:.2f}" for cur in currency_order
         )
 
         # Формуємо прибуток після округлення
         profit_rounded = " / ".join(
             f"{self.SYMBOLS[cur]}{p[f'profit_with_round_{cur}']:.2f}" for cur in currency_order
         )
 
         # Повертаємо фінальний блок тексту
         return (
             f"\n<b>📊 Чистий прибуток:</b> {profit}\n"
             f"<b>📊 Прибуток (з округленням):</b> {profit_rounded}"
         )
 
