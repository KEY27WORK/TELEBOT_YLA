"""
Модуль PriceCalculator (оптимізований).
Виконує розрахунок вартості товарів з урахуванням:
- Курсу долара
- Витрат на доставку
- Базової та скоригованої націнки

Використовує:
- ConfigService для завантаження курсу валют

Логування:
- Відстежує процес розрахунку на всіх етапах
"""

import logging
from core.config.config_service import ConfigService
from core.currency.currency_manager import CurrencyManager
from core.calculator.meest_delivery_service import MeestDeliveryService


class BasePriceCalculator:
    """Базовий клас для розрахунку ціни товарів"""

    DELIVERY_COST_PER_LB = 3.94  # Вартість доставки за фунт (USD)
    MONTHLY_FIXED_COST_PER_ITEM = 1  # Фіксовані витрати на AI (наприклад, $30 / 30 товарів = $1)
    FIXED_DELIVERY_COST = 15 / 30  # Фіксована доставка розподіляється між 30 товарами
    DISCOUNT_PERCENTAGE = 15  # Знижка за промокодом (в %)

    @classmethod
    def apply_discount(cls, price: float) -> float:
        """
        Застосовує глобальну знижку до товару

        :param price: Повна ціна товару
        :return: Ціна після знижки
        """
        return price * (1 - cls.DISCOUNT_PERCENTAGE / 100)

    @staticmethod
    def round_to_nearest_ten(value: float) -> float:
        """
        Округлює значення до найближчого десятка (зручно для гривень)

        :param value: Значення для округлення
        :return: Округлене значення
        """
        return (int(value / 10) + (1 if value % 10 != 0 else 0)) * 10

    @staticmethod
    def get_markup_percentage(price: float) -> int:
        """
        Визначає базовий відсоток націнки залежно від закупівельної ціни (в USD)

        :param price: Закупівельна ціна
        :return: Відсоток націнки
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
        """
        Коригує націнку залежно від частки витрат на доставку

        :param delivery_ratio: Частка доставки в собівартості (у %)
        :return: Корекція націнки
        """
        if delivery_ratio > 20:
            return -3
        elif delivery_ratio < 10:
            return 3
        return 0

    @staticmethod
    def get_symbol_currency(currency: str) -> str:
        """
        Повертає символ валюти за її кодом
        """
        if currency == 'USD':
            return '$'
        if currency == 'GBP':
            return '£'
        if currency == 'EUR':
            return '€'
        return ''

    @staticmethod
    def get_weight_kg(weight_lbs: float) -> float:
        """
        Конвертує вагу з фунтів у кілограми
        """
        return round(weight_lbs * 0.453592, 3)

    def convert_currency_block(self, base_amount: float, *rates: float) -> list:
        """
        Універсальна функція для конвертації базової суми через ланцюжок курсів
        Наприклад: EUR → USD → UAH

        :param base_amount: Початкова сума
        :param rates: Один або декілька курсів
        :return: Список конвертованих значень
        """
        results = []
        for i in range(len(rates)):
            rate_chain = 1
            for j in range(i + 1):
                rate_chain *= rates[j]
            results.append(round(base_amount * rate_chain, 2))
        return results

    def calculate(self, *args, **kwargs) -> dict:
        raise NotImplementedError("Метод calculate повинен бути реалізований у підкласі")


class BasePriceCalculatorEU(BasePriceCalculator):
    """🇪🇺 Базовий калькулятор для розрахунку цін у країнах Європи 🇪🇺"""

    FREE_SHIPPING_THRESHOLD = 100.0  # Безкоштовна доставка від €100
    LOCAL_DELIVERY_COST = 10.00      # Заглушка, уточнюється в дочірніх класах

    def __init__(self, all_uah_rates: dict, all_usd_rates: dict, all_eur_rates: dict):
        self.all_uah_rates = all_uah_rates
        self.all_usd_rates = all_usd_rates
        self.all_eur_rates = all_eur_rates

    def calculate_delivery(self, country: str, price: float, weight_kg: float) -> tuple:
        """🚛 Розрахунок локальної та Meest доставки з урахуванням знижки"""
        discounted_price = self.apply_discount(price)
        local_delivery = 0 if discounted_price >= self.FREE_SHIPPING_THRESHOLD else self.LOCAL_DELIVERY_COST

        meest_delivery = MeestDeliveryService.get_price(
            country=country,
            method="air",
            type_="courier",
            weight_kg=weight_kg
        )

        return round(local_delivery, 2), round(meest_delivery, 2)


# ----------------- Калькуляторы по регионам -----------------

class PriceCalculatorUSD(BasePriceCalculator):
    """🇺🇸 Калькулятор расчета цены для США (USD) 🇺🇸"""

    FREE_SHIPPING_THRESHOLD = 75.0  # Безкоштовна доставка по США від $75
    LOCAL_DELIVERY_COST = 6.99     # Локальна доставка по США, якщо ціна менше порогу

    def __init__(self, all_uah_rates: dict, all_eur_rates: dict):
        self.all_uah_rates = all_uah_rates
        self.all_eur_rates = all_eur_rates

    def calculate(self, price_usd: float, weight: float, currency: str) -> dict:
        logging.info(f"🔄 Початок розрахунку ціни для товару: ${price_usd}, вага: {weight} lbs")

        # 💱 Отримання актуального курсу USD → UAH
        logging.info(f"💱 Курс USD → UAH: {self.all_uah_rates.get('USD')}")
        logging.info(f"💱 Курс EUR → UAH: {self.all_uah_rates.get('EUR')}")
        logging.info(f"💱 Курс USD → EUR: {self.all_eur_rates.get('USD')}")

        # Урахування базової знижки за промокодом
        discounted_price = self.apply_discount(price_usd)

        # 🇺🇸 Визначення вартості локальної доставки по США
        us_delivery = 0.0 if discounted_price >= self.FREE_SHIPPING_THRESHOLD else self.LOCAL_DELIVERY_COST #нужно сравнивать не через price_usd а через discounted_price 

        # 🚚 Розрахунок доставки Meest (авіа + кур'єр)
        weight_kg = self.get_weight_kg(weight)
        meest_usd = MeestDeliveryService.get_price(
            country="US",
            method="air",
            type_="courier",
            weight_kg=weight_kg
        )

        # 💸 Загальна доставка
        delivery_usd = round(us_delivery + meest_usd, 2)
        logging.info(f"📦 Доставка Meest: ${meest_usd:.2f} + локальна ${us_delivery:.2f} = ${delivery_usd:.2f}")

        # 💰 Розрахунок собівартості (ціна зі знижкою + доставка + AI)
        cost_price = discounted_price + delivery_usd + self.MONTHLY_FIXED_COST_PER_ITEM

        logging.info(
            f"📊 Собівартість (USD): ${cost_price:.2f} "
            f"(ціна зі знижкою ${discounted_price:.2f}, AI: ${self.MONTHLY_FIXED_COST_PER_ITEM}, доставка: ${delivery_usd:.2f})"
        )

        # 📈 Накрутка з урахуванням доставки
        markup_percentage = self.get_markup_percentage(price_usd)
        delivery_ratio = (delivery_usd / cost_price) * 100
        markup_adjustment = self.get_markup_adjustment(delivery_ratio)
        markup_percentage += markup_adjustment

        # 🏷 Ціна продажу в USD та UAH
        sale_price_usd = cost_price * (1 + markup_percentage / 100) # Ціна в долларах
        sale_price_uah = sale_price_usd * self.all_uah_rates.get('USD') # Ціна в гривнях 
        sale_price_eur = sale_price_usd * self.all_eur_rates.get('USD') # Ціна в Euro 

        # 🔁 Округлення до зручної ціни
        sale_price_rounded_uah = self.round_to_nearest_ten(sale_price_uah) # Округлення в гривнях 
        sale_price_rounded_usd = sale_price_rounded_uah / self.all_uah_rates.get('USD') # Округлення в Dollars 
        sale_price_rounded_eur = sale_price_rounded_uah / self.all_uah_rates.get('EUR') # Округлення в Euro 

        return {
            # 💵 Ціна продажу
            "sale_price_usd": round(sale_price_usd, 2),
            "sale_price_eur": round(sale_price_eur, 2),
            "sale_price_uah": round(sale_price_uah, 2),
            "sale_price_rounded_usd": round(sale_price_rounded_usd, 2), # Округлення в долларах 
            "sale_price_rounded_eur": round(sale_price_rounded_eur, 2), # Округлення в евро 
            "sale_price_rounded_uah": round(sale_price_rounded_uah, 2),

            # 🧾 Собівартість
            "cost_price_usd": round(cost_price, 2),
            "cost_price_eur": round(cost_price * self.all_eur_rates.get('USD'), 2),
            "cost_price_uah": round(cost_price * self.all_uah_rates.get('USD'), 2),
            "cost_price_without_delivery_usd": round(cost_price - delivery_usd, 2),
            "cost_price_without_delivery_eur": round((cost_price - delivery_usd) * self.all_eur_rates.get('USD'), 2),
            "cost_price_without_delivery_uah": round((cost_price - delivery_usd) * self.all_uah_rates.get('USD'), 2),

            # 🚛 Доставка
            "us_delivery_usd": round(us_delivery, 2),
            "us_delivery_eur": round(us_delivery * self.all_eur_rates.get('USD'), 2),
            "us_delivery_uah": round(us_delivery * self.all_uah_rates.get('USD'), 2),

            "meest_delivery_usd": round(meest_usd, 2),
            "meest_delivery_eur": round(meest_usd * self.all_eur_rates.get('USD'), 2),
            "meest_delivery_uah": round(meest_usd * self.all_uah_rates.get('USD'), 2),

            "delivery_price_usd": round(delivery_usd, 2),
            "delivery_price_eur": round(delivery_usd * self.all_eur_rates.get('USD'), 2),
            "delivery_price_uah": round(delivery_usd * self.all_uah_rates.get('USD'), 2),

            # 📊 Накрутка
            "markup": markup_percentage,
            "markup_adjustment": markup_adjustment,

            # 💱 Курс валют
            "usd_rate": self.all_uah_rates.get('USD'),
            "eur_rate": self.all_uah_rates.get('EUR'),
            "usd-eur_rate": self.all_eur_rates.get('USD'),

            # 💵 Прибуток
            "profit_usd": round(sale_price_usd - cost_price, 2),
            "profit_eur": round(sale_price_eur - cost_price * self.all_eur_rates.get('USD'), 2),
            "profit_uah": round(sale_price_uah - cost_price * self.all_uah_rates.get('USD'), 2),
            "profit_with_round_usd": round(sale_price_rounded_usd - cost_price, 2),
            "profit_with_round_eur": round(sale_price_rounded_eur - cost_price * self.all_eur_rates.get('USD'), 2),
            "profit_with_round_uah": round(sale_price_rounded_uah - cost_price * self.all_uah_rates.get('USD'), 2),

            # 🔁 Округлення
            "round_usd": round(sale_price_rounded_usd - sale_price_usd, 2),
            "round_eur": round(sale_price_rounded_eur - sale_price_eur, 2),
            "round_uah": round(sale_price_rounded_uah - sale_price_uah, 2),

            # ⚖️ Вага посилки
            "weight_lbs" : weight,
            "weight_kg" : weight_kg
        }



class PriceCalculatorGBP(BasePriceCalculator):
    """🇬🇧 Калькулятор розрахунку ціни для Великобританії (GBP) 🇬🇧"""

    FREE_SHIPPING_THRESHOLD = 80.0  # Безкоштовна доставка від £80
    LOCAL_DELIVERY_COST = 6.50      # Локальна доставка по UK, якщо ціна менше порогу

    def __init__(self, all_uah_rates: dict, all_usd_rates: dict, all_eur_rates: dict):
        # Курси валют
        self.all_uah_rates = all_uah_rates  # Курси валют до гривні (UAH)
        self.all_usd_rates = all_usd_rates  # Курси валют до долара (USD)
        self.all_eur_rates = all_eur_rates  # Курси валют до євро (EUR)

    def calculate(self, price_gbp: float, weight: float, currency: str) -> dict:
        logging.info(f"🔄 Початок розрахунку ціни для товару: £{price_gbp}, вага: {weight} lbs")

        # 📉 Знижка за промокодом
        discounted_price_gbp = self.apply_discount(price_gbp)

        # 🚛 Локальна доставка (безкоштовно від порогу)
        uk_delivery_gbp = (
            0 if discounted_price_gbp >= self.FREE_SHIPPING_THRESHOLD else self.LOCAL_DELIVERY_COST
        )

        # ⚖️ Вага у кг
        weight_kg = self.get_weight_kg(weight)

        # ✈️ Доставка Meest
        meest_delivery_gbp = MeestDeliveryService.get_price(
            country="UK",
            method="air",
            type_="courier",
            weight_kg=weight_kg
        )

        # 💸 Повна вартість доставки
        delivery_price_gbp = uk_delivery_gbp + meest_delivery_gbp
        logging.info(
            f"📦 Доставка Meest: £{meest_delivery_gbp:.2f} + локальна £{uk_delivery_gbp:.2f} = £{delivery_price_gbp:.2f}"
        )

        # 🧾 Собівартість (товар + доставка + фікс витрати)
        cost_price_gbp = discounted_price_gbp + delivery_price_gbp + self.MONTHLY_FIXED_COST_PER_ITEM

        # 📊 Накрутка з урахуванням поправки
        markup_percentage = self.get_markup_percentage(discounted_price_gbp * self.all_usd_rates['GBP'])
        delivery_ratio = (delivery_price_gbp / cost_price_gbp) * 100
        markup_adjustment = self.get_markup_adjustment(delivery_ratio)
        markup_percentage += markup_adjustment

        # 💵 Ціна продажу (GBP → USD → UAH/EUR)
        sale_price_gbp = cost_price_gbp * (1 + markup_percentage / 100)
        sale_price_usd = sale_price_gbp * self.all_usd_rates['GBP']
        sale_price_uah = sale_price_usd * self.all_uah_rates['USD']
        sale_price_eur = sale_price_usd * self.all_eur_rates['USD']

        # 🔁 Округлення ціни в гривнях та конвертація назад в інші валюти
        sale_price_rounded_uah = self.round_to_nearest_ten(sale_price_uah)
        sale_price_rounded_usd = sale_price_rounded_uah / self.all_uah_rates['USD']
        sale_price_rounded_gbp = sale_price_rounded_usd / self.all_usd_rates['GBP']
        sale_price_rounded_eur = sale_price_rounded_usd * self.all_eur_rates['USD']

        return {
            # 💵 Ціна продажу
            "sale_price_gbp": round(sale_price_gbp, 2),
            "sale_price_usd": round(sale_price_usd, 2),
            "sale_price_eur": round(sale_price_eur, 2),
            "sale_price_uah": round(sale_price_uah, 2),
            "sale_price_rounded_gbp": round(sale_price_rounded_gbp, 2),
            "sale_price_rounded_usd": round(sale_price_rounded_usd, 2),
            "sale_price_rounded_eur": round(sale_price_rounded_eur, 2),
            "sale_price_rounded_uah": round(sale_price_rounded_uah, 2),

            # 🧾 Собівартість (повна)
            "cost_price_gbp": round(cost_price_gbp, 2),
            "cost_price_usd": round(cost_price_gbp * self.all_usd_rates['GBP'], 2),
            "cost_price_eur": round(cost_price_gbp * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "cost_price_uah": round(cost_price_gbp * self.all_uah_rates['GBP'], 2),

            # 🧾 Собівартість без доставки
            "cost_price_without_delivery_gbp": round(cost_price_gbp - delivery_price_gbp, 2),
            "cost_price_without_delivery_usd": round((cost_price_gbp - delivery_price_gbp) * self.all_usd_rates['GBP'], 2),
            "cost_price_without_delivery_eur": round((cost_price_gbp - delivery_price_gbp) * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "cost_price_without_delivery_uah": round((cost_price_gbp - delivery_price_gbp) * self.all_uah_rates['GBP'], 2),

            # 🚛 Доставка по Британії
            "uk_delivery_gbp": round(uk_delivery_gbp, 2),
            "uk_delivery_usd": round(uk_delivery_gbp * self.all_usd_rates['GBP'], 2),
            "uk_delivery_eur": round(uk_delivery_gbp * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "uk_delivery_uah": round(uk_delivery_gbp * self.all_uah_rates['GBP'], 2),

            # 🚛 Доставка Meest
            "meest_delivery_gbp": round(meest_delivery_gbp, 2),
            "meest_delivery_usd": round(meest_delivery_gbp * self.all_usd_rates['GBP'], 2),
            "meest_delivery_eur": round(meest_delivery_gbp * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "meest_delivery_uah": round(meest_delivery_gbp * self.all_uah_rates['GBP'], 2),

            # 🚛 Загальна вартість доставки
            "delivery_price_gbp": round(delivery_price_gbp, 2),
            "delivery_price_usd": round(delivery_price_gbp * self.all_usd_rates['GBP'], 2),
            "delivery_price_eur": round(delivery_price_gbp * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "delivery_price_uah": round(delivery_price_gbp * self.all_uah_rates['GBP'], 2),

            # 📊 Накрутка
            "markup": markup_percentage,
            "markup_adjustment": markup_adjustment,

            # 💱 Курси валют
            "usd_rate": self.all_uah_rates.get('USD'),
            "eur_rate": self.all_uah_rates.get('EUR'),
            "gbp_rate": self.all_uah_rates.get('GBP'),
            "gbp_usd_rate": self.all_usd_rates['GBP'],
            "usd_eur_rate": self.all_eur_rates.get('USD'),

            # 💵 Прибуток (без округлення)
            "profit_gbp": round(sale_price_gbp - cost_price_gbp, 2),
            "profit_usd": round(sale_price_usd - cost_price_gbp * self.all_usd_rates['GBP'], 2),
            "profit_eur": round(sale_price_eur - cost_price_gbp * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "profit_uah": round(sale_price_uah - cost_price_gbp * self.all_uah_rates['GBP'], 2),

            # 💵 Прибуток (з округленням)
            "profit_with_round_gbp": round(sale_price_rounded_gbp - cost_price_gbp, 2),
            "profit_with_round_usd": round(sale_price_rounded_usd - cost_price_gbp * self.all_usd_rates['GBP'], 2),
            "profit_with_round_eur": round(sale_price_rounded_eur - cost_price_gbp * self.all_usd_rates['GBP'] * self.all_eur_rates['USD'], 2),
            "profit_with_round_uah": round(sale_price_rounded_uah - cost_price_gbp * self.all_uah_rates['GBP'], 2),

            # 🔁 Округлення
            "round_gbp": round(sale_price_rounded_gbp - sale_price_gbp, 2),
            "round_usd": round(sale_price_rounded_usd - sale_price_usd, 2),
            "round_eur": round(sale_price_rounded_eur - sale_price_eur, 2),
            "round_uah": round(sale_price_rounded_uah - sale_price_uah, 2),

            # ⚖️ Вага посилки
            "weight_lbs": weight,
            "weight_kg": weight_kg
        }



class PriceCalculatorGermany(BasePriceCalculatorEU):
    """🇩🇪 Калькулятор розрахунку ціни для Німеччини (EUR) 🇩🇪"""

    LOCAL_DELIVERY_COST = 4.99  # Локальна доставка до складу Meest у Німеччині

    def calculate(self, price_eur: float, weight: float, currency: str) -> dict:
        logging.info(f"🔄 Початок розрахунку ціни для товару: €{price_eur}, вага: {weight} lbs")

        # 📉 Знижка за промокодом
        discounted_price_eur = self.apply_discount(price_eur)

        # 🚛 Локальна доставка (безкоштовно від €100)
        eu_delivery_eur = (
            0 if discounted_price_eur >= self.FREE_SHIPPING_THRESHOLD else self.LOCAL_DELIVERY_COST
        )

        # ⚖️ Вага у кг
        weight_kg = self.get_weight_kg(weight)

        # ✈️ Доставка Meest
        meest_delivery_eur = MeestDeliveryService.get_price(
            country="Germany",
            method="air",
            type_="courier",
            weight_kg=weight_kg
        )

        # 💸 Повна вартість доставки
        delivery_price_eur = eu_delivery_eur + meest_delivery_eur
        logging.info(
            f"📦 Доставка Meest: €{meest_delivery_eur:.2f} + локальна €{eu_delivery_eur:.2f} = €{delivery_price_eur:.2f}"
        )

        # 🧾 Собівартість (товар + доставка + AI)
        cost_price_eur = discounted_price_eur + delivery_price_eur + self.MONTHLY_FIXED_COST_PER_ITEM

        # 📊 Накрутка з поправкою на доставку
        markup_percentage = self.get_markup_percentage(discounted_price_eur * self.all_usd_rates['EUR'])
        delivery_ratio = (delivery_price_eur / cost_price_eur) * 100
        markup_adjustment = self.get_markup_adjustment(delivery_ratio)
        markup_percentage += markup_adjustment

        # 💵 Ціна продажу (EUR → USD → UAH)
        sale_price_eur = cost_price_eur * (1 + markup_percentage / 100)
        sale_price_usd = sale_price_eur * self.all_usd_rates['EUR']
        sale_price_uah = sale_price_usd * self.all_uah_rates['USD']

        # 🔁 Округлення до гривні та конвертація назад
        sale_price_rounded_uah = self.round_to_nearest_ten(sale_price_uah)
        sale_price_rounded_usd = sale_price_rounded_uah / self.all_uah_rates['USD']
        sale_price_rounded_eur = sale_price_rounded_usd / self.all_usd_rates['EUR']

        # 📦 Фінальний результат (усі валюти та розрахунки)
        return {
            # 💵 Ціна продажу (EUR/USD/UAH)
            "sale_price_eur": round(sale_price_eur, 2),
            "sale_price_usd": round(sale_price_usd, 2),
            "sale_price_uah": round(sale_price_uah, 2),
            "sale_price_rounded_eur": round(sale_price_rounded_eur, 2),
            "sale_price_rounded_usd": round(sale_price_rounded_usd, 2),
            "sale_price_rounded_uah": round(sale_price_rounded_uah, 2),

            # 🧾 Собівартість (повна, усі валюти)
            "cost_price_eur": round(cost_price_eur, 2),
            "cost_price_usd": round(cost_price_eur * self.all_usd_rates['EUR'], 2),
            "cost_price_uah": round(cost_price_eur * self.all_uah_rates['EUR'], 2),

            # 🧾 Собівартість без доставки
            "cost_price_without_delivery_eur": round(cost_price_eur - delivery_price_eur, 2),
            "cost_price_without_delivery_usd": round((cost_price_eur - delivery_price_eur) * self.all_usd_rates['EUR'], 2),
            "cost_price_without_delivery_uah": round((cost_price_eur - delivery_price_eur) * self.all_uah_rates['EUR'], 2),

            # 🚛 Доставка по Європі
            "eu_delivery_eur": round(eu_delivery_eur, 2),
            "eu_delivery_usd": round(eu_delivery_eur * self.all_usd_rates['EUR'], 2),
            "eu_delivery_uah": round(eu_delivery_eur * self.all_uah_rates['EUR'], 2),

            # 🚛 Доставка Meest
            "meest_delivery_eur": round(meest_delivery_eur, 2),
            "meest_delivery_usd": round(meest_delivery_eur * self.all_usd_rates['EUR'], 2),
            "meest_delivery_uah": round(meest_delivery_eur * self.all_uah_rates['EUR'], 2),

            # 🚛 Повна доставка
            "delivery_price_eur": round(delivery_price_eur, 2),
            "delivery_price_usd": round(delivery_price_eur * self.all_usd_rates['EUR'], 2),
            "delivery_price_uah": round(delivery_price_eur * self.all_uah_rates['EUR'], 2),

            # 📊 Накрутка
            "markup": markup_percentage,
            "markup_adjustment": markup_adjustment,

            # 💱 Курси валют
            "eur_rate": self.all_uah_rates['EUR'],
            "usd_rate": self.all_uah_rates['USD'],
            "eur_usd_rate": self.all_usd_rates['EUR'],

            # 💵 Прибуток (без округлення)
            "profit_eur": round(sale_price_eur - cost_price_eur, 2),
            "profit_usd": round(sale_price_usd - cost_price_eur * self.all_usd_rates['EUR'], 2),
            "profit_uah": round(sale_price_uah - cost_price_eur * self.all_uah_rates['EUR'], 2),

            # 💵 Прибуток (з округленням)
            "profit_with_round_eur": round(sale_price_rounded_eur - cost_price_eur, 2),
            "profit_with_round_usd": round(sale_price_rounded_usd - cost_price_eur * self.all_usd_rates['EUR'], 2),
            "profit_with_round_uah": round(sale_price_rounded_uah - cost_price_eur * self.all_uah_rates['EUR'], 2),

            # 🔁 Округлення
            "round_eur": round(sale_price_rounded_eur - sale_price_eur, 2),
            "round_usd": round(sale_price_rounded_usd - sale_price_usd, 2),
            "round_uah": round(sale_price_rounded_uah - sale_price_uah, 2),

            # ⚖️ Вага посилки
            "weight_lbs": weight,
            "weight_kg": weight_kg
        }



class PriceCalculatorPoland(BasePriceCalculatorEU):
    """🇵🇱 Калькулятор розрахунку ціни для Польщі (PLN як основна валюта) 🇵🇱"""

    LOCAL_DELIVERY_COST = 48.00  # Доставка до складу Meest у Польщі (PLN)

    def __init__(self, all_uah_rates: dict, all_usd_rates: dict, all_eur_rates: dict):
        # Курси валют для PLN, USD, EUR, UAH
        self.all_uah_rates = all_uah_rates
        self.all_usd_rates = all_usd_rates
        self.all_eur_rates = all_eur_rates

    def calculate(self, price_pln: float, weight: float, currency: str) -> dict:
        logging.info(f"🔄 Початок розрахунку ціни для товару: {price_pln} zł, вага: {weight} lbs")

        # 📉 Знижка за промокодом
        discounted_price_pln = self.apply_discount(price_pln)

        # 🚛 Локальна доставка по Польщі (безкоштовно від порогу €100 у PLN)
        eu_delivery_pln = (
            0 if discounted_price_pln >= self.FREE_SHIPPING_THRESHOLD * self.all_eur_rates['PLN']
            else self.LOCAL_DELIVERY_COST
        )

        # ⚖️ Вага у кг
        weight_kg = self.get_weight_kg(weight)

        # ✈️ Доставка Meest у PLN
        meest_delivery_pln = MeestDeliveryService.get_price(
            country="Poland",
            method="air",
            type_="courier",
            weight_kg=weight_kg
        )

        # 💸 Повна доставка
        delivery_price_pln = eu_delivery_pln + meest_delivery_pln
        logging.info(
            f"📦 Доставка Meest: {meest_delivery_pln:.2f} zł + локальна {eu_delivery_pln:.2f} zł = {delivery_price_pln:.2f} zł"
        )

        # 🧾 Собівартість (товар + доставка + AI)
        cost_price_pln = discounted_price_pln + delivery_price_pln + self.MONTHLY_FIXED_COST_PER_ITEM

        # 📊 Накрутка з урахуванням доставки
        markup_percentage = self.get_markup_percentage(discounted_price_pln * self.all_usd_rates['PLN'])
        delivery_ratio = (delivery_price_pln / cost_price_pln) * 100
        markup_adjustment = self.get_markup_adjustment(delivery_ratio)
        markup_percentage += markup_adjustment

        # 💵 Ціна продажу (PLN → USD → EUR → UAH)
        sale_price_pln = cost_price_pln * (1 + markup_percentage / 100)
        sale_price_usd = sale_price_pln * self.all_usd_rates['PLN']
        sale_price_eur = sale_price_usd * self.all_eur_rates['USD']
        sale_price_uah = sale_price_usd * self.all_uah_rates['USD']

        # 🔁 Округлення до гривень і конвертація назад
        sale_price_rounded_uah = self.round_to_nearest_ten(sale_price_uah)
        sale_price_rounded_usd = sale_price_rounded_uah / self.all_uah_rates['USD']
        sale_price_rounded_pln = sale_price_rounded_usd / self.all_usd_rates['PLN']
        sale_price_rounded_eur = sale_price_rounded_usd * self.all_eur_rates['USD']

        # 📦 Фінальний результат (усі валюти та розрахунки)
        return {
            # 💵 Ціна продажу (PLN/USD/EUR/UAH)
            "sale_price_pln": round(sale_price_pln, 2),
            "sale_price_usd": round(sale_price_usd, 2),
            "sale_price_eur": round(sale_price_eur, 2),
            "sale_price_uah": round(sale_price_uah, 2),
            "sale_price_rounded_pln": round(sale_price_rounded_pln, 2),
            "sale_price_rounded_usd": round(sale_price_rounded_usd, 2),
            "sale_price_rounded_eur": round(sale_price_rounded_eur, 2),
            "sale_price_rounded_uah": round(sale_price_rounded_uah, 2),

            # 🧾 Собівартість (повна, всі валюти)
            "cost_price_pln": round(cost_price_pln, 2),
            "cost_price_usd": round(cost_price_pln * self.all_usd_rates['PLN'], 2),
            "cost_price_eur": round(cost_price_pln * self.all_usd_rates['PLN'] * self.all_eur_rates['USD'], 2),
            "cost_price_uah": round(cost_price_pln * self.all_uah_rates['PLN'], 2),

            # 🧾 Собівартість без доставки
            "cost_price_without_delivery_pln": round(cost_price_pln - delivery_price_pln, 2),
            "cost_price_without_delivery_usd": round((cost_price_pln - delivery_price_pln) * self.all_usd_rates['PLN'], 2),
            "cost_price_without_delivery_uah": round((cost_price_pln - delivery_price_pln) * self.all_uah_rates['PLN'], 2),

            # 🚛 Доставка локальна (Польща)
            "pl_delivery_pln": round(eu_delivery_pln, 2),
            "pl_delivery_usd": round(eu_delivery_pln * self.all_usd_rates['PLN'], 2),
            "pl_delivery_uah": round(eu_delivery_pln * self.all_uah_rates['PLN'], 2),

            # 🚛 Доставка Meest
            "meest_delivery_pln": round(meest_delivery_pln, 2),
            "meest_delivery_usd": round(meest_delivery_pln * self.all_usd_rates['PLN'], 2),
            "meest_delivery_uah": round(meest_delivery_pln * self.all_uah_rates['PLN'], 2),

            # 🚛 Повна доставка
            "delivery_price_pln": round(delivery_price_pln, 2),
            "delivery_price_usd": round(delivery_price_pln * self.all_usd_rates['PLN'], 2),
            "delivery_price_uah": round(delivery_price_pln * self.all_uah_rates['PLN'], 2),

            # 📊 Накрутка
            "markup": markup_percentage,
            "markup_adjustment": markup_adjustment,

            # 💱 Курси валют
            "pln_rate": self.all_uah_rates['PLN'],
            "usd_rate": self.all_uah_rates['USD'],
            "eur_rate": self.all_uah_rates['EUR'],
            "pln_usd_rate": self.all_usd_rates['PLN'],
            "usd_eur_rate": self.all_eur_rates['USD'],

            # 💵 Прибуток (без округлення)
            "profit_pln": round(sale_price_pln - cost_price_pln, 2),
            "profit_usd": round(sale_price_usd - cost_price_pln * self.all_usd_rates['PLN'], 2),
            "profit_uah": round(sale_price_uah - cost_price_pln * self.all_uah_rates['PLN'], 2),

            # 💵 Прибуток (з округленням)
            "profit_with_round_pln": round(sale_price_rounded_pln - cost_price_pln, 2),
            "profit_with_round_usd": round(sale_price_rounded_usd - cost_price_pln * self.all_usd_rates['PLN'], 2),
            "profit_with_round_uah": round(sale_price_rounded_uah - cost_price_pln * self.all_uah_rates['PLN'], 2),

            # 🔁 Округлення
            "round_pln": round(sale_price_rounded_pln - sale_price_pln, 2),
            "round_usd": round(sale_price_rounded_usd - sale_price_usd, 2),
            "round_uah": round(sale_price_rounded_uah - sale_price_uah, 2),

            # ⚖️ Вага посилки
            "weight_lbs": weight,
            "weight_kg": weight_kg
        }



class PriceCalculatorFactory:
    """
    🏭 Фабрика калькуляторів цін за валютою.
    Обирає відповідний калькулятор залежно від валюти товару.
    Підтримує USD, EUR, GBP, PLN.
    """

    def __init__(self, currency_manager: CurrencyManager):
        self.currency_manager = currency_manager  # Менеджер курсів валют

    def get_calculator(self, currency: str):
        currency = currency.upper()

        # 🔄 Отримання всіх актуальних курсів
        all_uah_rates = self.currency_manager.get_all_rates()

        # 🔁 Конверсії між валютами
        eur_to_usd = self.currency_manager.convert(1, "EUR", "USD", all_uah_rates)
        gbp_to_usd = self.currency_manager.convert(1, "GBP", "USD", all_uah_rates)
        pln_to_usd = self.currency_manager.convert(1, "PLN", "USD", all_uah_rates)

        usd_to_eur = self.currency_manager.convert(1, "USD", "EUR", all_uah_rates)
        gbp_to_eur = self.currency_manager.convert(1, "GBP", "EUR", all_uah_rates)
        pln_to_eur = self.currency_manager.convert(1, "PLN", "EUR", all_uah_rates)

        # 📦 Всі курси по валютам
        all_usd_rates = {"EUR": eur_to_usd, "GBP": gbp_to_usd, "PLN": pln_to_usd}
        all_eur_rates = {"USD": usd_to_eur, "GBP": gbp_to_eur, "PLN": pln_to_eur}


        # 🧮 Вибір відповідного калькулятора
        if currency == "USD":
            return PriceCalculatorUSD(all_uah_rates, all_eur_rates)

        elif currency == "GBP":
            return PriceCalculatorGBP(all_uah_rates, all_usd_rates, all_eur_rates)

        elif currency == "EUR":
            return PriceCalculatorGermany(all_uah_rates, all_usd_rates, all_eur_rates)

        elif currency == "PLN":
            return PriceCalculatorPoland(all_uah_rates, all_usd_rates, all_eur_rates)

        raise ValueError(f"❌ Непідтримувана валюта: {currency}")
