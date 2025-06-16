"""""
💰 price_service.py — Сервіс розрахунку повної вартості товару для Telegram-бота.

🔹 Основний функціонал:
- Знижка (15%)
- AI комісія ($1)
- Динамічна націнка
- Delivery ratio (корекція націнки)
- Округлення: через гривню та зворотна конвертація

🔧 Використовує:
- CurrencyConverter — для конвертації курсів валют
"""

# 📦 Стандартні бібліотеки
from typing import Dict

# 🧱 Внутрішні модулі
from core.calculator.currency_converter import CurrencyConverter


# === 📉 Discount Service ===
class DiscountService:
    """🎁 Сервіс для розрахунку знижки."""
    DISCOUNT_PERCENTAGE = 15  # % знижка по промокоду

    @classmethod
    def apply_discount(cls, price: float) -> float:
        """📉 Застосування глобальної знижки до ціни."""
        return price * (1 - cls.DISCOUNT_PERCENTAGE / 100)


# === 🚚 Delivery Service ===
class DeliveryService:
    """🚚 Сервіс для розрахунку доставки."""
    LOCAL_DELIVERY = {
        "USD": 6.99,
        "EUR": 8.99,
        "GBP": 7.49,
        "PLN": 22.99
    }
    AI_COMMISSION = 1.0  # $1 — AI фіксована комісія

    @classmethod
    def calculate_local_delivery(cls, currency: str) -> float:
        """📦 Локальна доставка по регіону."""
        return cls.LOCAL_DELIVERY.get(currency, 6.99)

    @classmethod
    def calculate_meest_delivery(cls, weight: float) -> float:
        """✈️ Доставка Meest залежно від ваги.

        🔹 Логіка тарифу Meest для США:
        - до 1 фунта (приблизно 0.45 кг): фіксована ставка $5.90
        - за кожен додатковий фунт понад 1 додається $3.50

        🔸 Формула після 1 фунта:
        full_price = $5.90 + ($3.50 * (вага - 1 фунт))
        """
        if weight <= 1:
            return 5.90  # 📦 Мінімальна доставка для легких посилок
        return 5.90 + (weight - 1) * 3.5  # 📦 Збільшення ціни за додаткову вагу



# === 📈 Markup Service ===
class MarkupService:
    """📈 Сервіс для розрахунку націнки (маржинальної логіки).

    🔹 Відповідає за:
    - базову націнку по закупівельній ціні
    - корекцію націнки в залежності від частки доставки у повній собівартості
    """

    @staticmethod
    def get_markup_percentage(price: float) -> int:
        """📊 Базова націнка за закупівельною ціною.

        🔸 Логіка по діапазонам:
        - < $20 → 30%
        - < $30 → 27%
        - < $40 → 25%
        - < $50 → 23%
        - $50+ → 20%
        """
        if price < 20:
            return 30
        elif price < 30:
            return 27
        elif price < 40:
            return 25
        elif price < 50:
            return 23
        return 20

    @staticmethod
    def get_markup_adjustment(delivery_ratio: float) -> int:
        """⚖️ Корекція націнки в залежності від частки доставки у собівартості.

        🔸 Логіка:
        - якщо доставка > 20% → зменшуємо націнку на -3%
        - якщо доставка < 10% → збільшуємо націнку на +3%
        - інакше — залишаємо без змін
        """
        if delivery_ratio > 20:
            return -3
        elif delivery_ratio < 10:
            return 3
        return 0

    @classmethod
    def calculate_final_markup(cls, price: float, delivery: float, cost_with_delivery: float) -> (float, float):
        """📐 Підсумкова націнка з урахуванням вартості доставки.

        🔄 Алгоритм:
        1️⃣ Розраховуємо базову націнку по закупівельній ціні.
        2️⃣ Обчислюємо delivery_ratio = частка доставки в повній собівартості.
        3️⃣ Додаємо корекцію націнки згідно delivery_ratio.
        4️⃣ Повертаємо: (підсумкова націнка, корекція).
        """
        base = cls.get_markup_percentage(price)  # 📊 Базова націнка
        delivery_ratio = (delivery / cost_with_delivery) * 100  # ⚖️ Частка доставки у % від собівартості
        adjust = cls.get_markup_adjustment(delivery_ratio)  # 📉 Корекція в залежності від частки
        return base + adjust, adjust  # 🔙 Повертаємо підсумковий % та саму корекцію



# === 🔄 Rounding Service ===
class RoundingService:
    """🔢 Сервіс округлення ціни."""

    @staticmethod
    def round_to_nearest_ten(value: float) -> float:
        """🔄 Округлення до найближчого десятка."""
        return (int(value / 10) + (1 if value % 10 != 0 else 0)) * 10


# === 💸 Product Price Service ===
class ProductPriceService:
    """💸 Основний сервіс розрахунку повної ціни товару."""

    def __init__(self, currency_converter: CurrencyConverter):
        self.currency_converter = currency_converter

    def calculate(self, price: float, weight: float, currency: str) -> Dict[str, float]:
        """📊 Повний розрахунок ціни з усіма етапами."""
        # 🔄 Конвертація в USD
        price_usd = self.currency_converter.convert(price, currency, "USD")

        # 📉 Знижка
        discounted_price = DiscountService.apply_discount(price_usd)

        # 🚚 Доставка
        base_delivery = DeliveryService.calculate_local_delivery("USD")
        meest_delivery = DeliveryService.calculate_meest_delivery(weight)
        full_delivery = base_delivery + meest_delivery

        # 🧾 Собівартість
        cost_without_delivery = discounted_price + DeliveryService.AI_COMMISSION
        cost_with_delivery = cost_without_delivery + full_delivery

        # 📈 Накрутка (розрахунок маржинальної націнки)
        final_markup, markup_adjustment = MarkupService.calculate_final_markup(
            price_usd, full_delivery, cost_with_delivery
        )
        sale_price = cost_with_delivery * (1 + final_markup / 100)  # 💵 Ціна продажу до округлення
        profit = sale_price - cost_with_delivery  # 📊 Прибуток до округлення

        # 🔢 Округлення фінальної ціни через гривню (центральна валюта округлення)
        usd_to_uah = self.currency_converter.convert(1, "USD", "UAH")  # 🔄 Отримуємо курс USD → UAH
        sale_price_uah = sale_price * usd_to_uah  # 💵 Конвертація фінальної ціни в гривню
        sale_price_rounded_uah = RoundingService.round_to_nearest_ten(sale_price_uah)  # 🔄 Округлення в гривні (по 10 грн)
        sale_price_rounded = sale_price_rounded_uah / usd_to_uah  # 🔁 Зворотня конвертація назад в USD після округлення
        profit_rounded = sale_price_rounded - cost_with_delivery  # 📊 Прибуток після округлення

        # 📦 Початкове формування фінального результату (починаємо збирати всі розрахунки)
        result = {
            "weight_lbs": weight,  # ⚖️ Вага товару в фунтах
            "markup": final_markup,  # 📈 Підсумкова націнка
            "markup_adjustment": markup_adjustment,  # 📉 Корекція націнки
        }

        # 🔁 Розрахунок суми округлення (дельта між округленою та реальною ціною в гривні)
        delta_uah = sale_price_rounded_uah - sale_price_uah

        # 🔄 Конвертація дельти округлення в інші валюти (через гривню)
        eur_to_uah = self.currency_converter.convert(1, "EUR", "UAH")
        gbp_to_uah = self.currency_converter.convert(1, "GBP", "UAH")
        pln_to_uah = self.currency_converter.convert(1, "PLN", "UAH")

        # 📊 Запис розрахованих дельт по кожній валюті в результат
        result["round_usd"] = round(delta_uah / usd_to_uah, 2)
        result["round_eur"] = round(delta_uah / eur_to_uah, 2)
        result["round_gbp"] = round(delta_uah / gbp_to_uah, 2)
        result["round_pln"] = round(delta_uah / pln_to_uah, 2)
        result["round_uah"] = round(delta_uah, 2)

        # 🔄 Конвертація по всім валютам (основний цикл формування фінального result)
        for target_currency in ["USD", "EUR", "GBP", "PLN", "UAH"]:
            try:
                # 🔢 Конвертуємо кожну метрику в target_currency
                converted_sale_price = self.currency_converter.convert(sale_price, "USD", target_currency)
                converted_sale_rounded = self.currency_converter.convert(sale_price_rounded, "USD", target_currency)
                converted_cost = self.currency_converter.convert(cost_with_delivery, "USD", target_currency)
                converted_profit = self.currency_converter.convert(profit, "USD", target_currency)
                converted_profit_rounded = self.currency_converter.convert(profit_rounded, "USD", target_currency)
                converted_base_delivery = self.currency_converter.convert(base_delivery, "USD", target_currency)
                converted_meest_delivery = self.currency_converter.convert(meest_delivery, "USD", target_currency)
                converted_full_delivery = self.currency_converter.convert(full_delivery, "USD", target_currency)
                converted_discounted = self.currency_converter.convert(discounted_price, "USD", target_currency)

                # 🔑 Формуємо ключ для запису в result (usd / eur / gbp / pln / uah)
                cur_key = target_currency.lower()

                # 📊 Записуємо всі розраховані значення в result
                result[f"sale_price_{cur_key}"] = converted_sale_price  # Ціна без округлення
                result[f"sale_price_rounded_{cur_key}"] = converted_sale_rounded  # Ціна після округлення
                result[f"{self._local_delivery_key(currency)}_{cur_key}"] = converted_base_delivery  # Локальна доставка
                result[f"meest_delivery_{cur_key}"] = converted_meest_delivery  # Meest доставка
                result[f"delivery_price_{cur_key}"] = converted_full_delivery  # Повна доставка
                result[f"cost_price_without_delivery_{cur_key}"] = converted_discounted + DeliveryService.AI_COMMISSION  # Собівартість без доставки
                result[f"cost_price_{cur_key}"] = converted_cost  # Собівартість з доставкою
                result[f"profit_{cur_key}"] = converted_profit  # Прибуток до округлення
                result[f"profit_with_round_{cur_key}"] = converted_profit_rounded  # Прибуток після округлення

            except ValueError:
                # 🛑 Пропускаємо валюту якщо нема курсу
                continue

        return result

    def _local_delivery_key(self, currency: str) -> str:
        """🗺 Повертає ключ для локальної доставки по регіону."""
        return {
            "USD": "us_delivery",
            "EUR": "eu_delivery",
            "GBP": "uk_delivery",
            "PLN": "pl_delivery"
        }.get(currency, "us_delivery")
