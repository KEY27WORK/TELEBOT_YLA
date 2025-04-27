"""
📦 meest_delivery_service.py — сервіс для розрахунку доставки Meest із різних країн.

🔹 Клас:
- `MeestDeliveryService` — централізовано рахує тарифи доставки Meest:
  - підтримує країни: США, Британія, Німеччина, Польща
  - різні методи доставки (авіа, море, НП)
  - різні типи доставки (кур'єр, відділення)

Використовує:
- Стандартний Python (без додаткових залежностей)
- Логування для відстеження процесу та помилок
"""

# 📚 Імпорти
import logging
from typing import Optional


class MeestDeliveryService:
    """
    🚚 Сервіс розрахунку вартості доставки Meest для різних країн та методів.
    """

    @classmethod
    def get_price(
        cls,
        country: str,
        method: str,
        type_: str,
        weight_kg: float,
        volumetric_weight_kg: Optional[float] = None
    ) -> float:
        """
        💸 Розраховує вартість доставки Meest.

        :param country: Країна відправки (US, UK, Germany, Poland)
        :param method: Метод доставки (air, sea, np_air, np_sea)
        :param type_: Тип доставки (courier, branch)
        :param weight_kg: Фактична вага (кг)
        :param volumetric_weight_kg: Об'ємна вага (опціонально, кг)
        :return: Ціна в локальній валюті країни
        """
        country = country.lower()
        method = method.lower()
        type_ = type_.lower()

        logging.info(f"📦 Розрахунок доставки Meest: країна={country}, метод={method}, тип={type_}, вага={weight_kg} кг")

        if country == "us" and method == "air":
            return cls._get_us_air_price(weight_kg)

        if country == "uk" and method == "air":
            return cls._get_uk_air_price(weight_kg)

        if country == "germany" and method == "air":
            return cls._get_germany_price(weight_kg)

        if country == "poland" and method == "air":
            return cls._get_poland_price(weight_kg)

        logging.error(f"❌ Не підтримується комбінація параметрів: {country}, {method}, {type_}")
        raise ValueError(f"❌ Непідтримувана конфігурація: {country}, {method}, {type_}")

    @staticmethod
    def _get_us_air_price(weight_kg: float) -> float:
        """
        🇺🇸 Тарифи Meest США (авіа + кур'єр):
        - до 0.5 кг: $5.90
        - понад 0.5 кг: $8.69/кг (мінімум $8.19)
        """
        if weight_kg <= 0.5:
            price = 5.90
        else:
            price = max(8.69 * weight_kg, 8.19)

        logging.debug(f"🇺🇸 США (авіа): {weight_kg} кг → ${price:.2f}")
        return price

    @staticmethod
    def _get_uk_air_price(weight_kg: float) -> float:
        """
        🇬🇧 Тарифи Meest Британія (авіа):
        - до 2 кг: £8.05 + £1.45/кг
        - до 10 кг: £5.15 + £2.55/кг
        - понад 10 кг: £5.15 + £2.45/кг
        """
        if weight_kg <= 2:
            price = 8.05 + 1.45 * weight_kg
        elif weight_kg <= 10:
            price = 5.15 + 2.55 * weight_kg
        else:
            price = 5.15 + 2.45 * weight_kg

        logging.debug(f"🇬🇧 Британія (авіа): {weight_kg} кг → £{price:.2f}")
        return price

    @staticmethod
    def _get_germany_price(weight_kg: float) -> float:
        """
        🇩🇪 Тарифи Meest Німеччина (авіа, EUR):
        - до 0.5 кг: €5.00
        - до 2.25 кг: €9.50
        - до 5 кг: €4.50/кг
        - до 10 кг: €3.75/кг
        - до 20 кг: €3.50/кг
        - понад 20 кг: €3.30/кг
        """
        if weight_kg <= 0.5:
            price = 5.00
        elif weight_kg <= 2.25:
            price = 9.50
        elif weight_kg <= 5.00:
            price = 4.50 * weight_kg
        elif weight_kg <= 10.00:
            price = 3.75 * weight_kg
        elif weight_kg <= 20.00:
            price = 3.50 * weight_kg
        else:
            price = 3.30 * weight_kg

        logging.debug(f"🇩🇪 Німеччина (авіа): {weight_kg} кг → €{price:.2f}")
        return price

    @staticmethod
    def _get_poland_price(weight_kg: float) -> float:
        """
        🇵🇱 Тарифи Meest Польща (авіа, PLN):
        - до 0.5 кг: 5 PLN
        - до 2.55 кг: 7.50 PLN
        - до 5 кг: 3.25 PLN/кг
        - до 10 кг: 2.60 PLN/кг
        - до 20 кг: 2.25 PLN/кг
        - понад 20 кг: 2.10 PLN/кг
        """
        if weight_kg <= 0.5:
            price = 5.00
        elif weight_kg <= 2.55:
            price = 7.50
        elif weight_kg <= 5.00:
            price = 3.25 * weight_kg
        elif weight_kg <= 10.00:
            price = 2.60 * weight_kg
        elif weight_kg <= 20.00:
            price = 2.25 * weight_kg
        else:
            price = 2.10 * weight_kg

        logging.debug(f"🇵🇱 Польща (авіа): {weight_kg} кг → {price:.2f} PLN")
        return price
