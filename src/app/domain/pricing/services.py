# 📦 app/domain/pricing/services.py
"""
📦 services.py — Чистые доменные сервисы для расчёта цены товара.
"""
# 🔠 Системные импорты
from dataclasses import dataclass
from typing import Tuple
import math

# 🧩 Внутренние модули проекта
from app.infrastructure.delivery.meest_delivery_service import MeestDeliveryService
from .interfaces import IPricingService, PricingContext, FullPriceDetails

# ==================================
# 🏛️ ВСПОМОГАТЕЛЬНЫЕ СЕРВИСЫ
# ==================================

class ProtectionService:
    """🛡️ Розраховує вартість страховки Navidium на основі точних тарифних порогів."""

    @staticmethod
    def get_protection_cost(price_usd: float) -> float:
        """
        Визначає вартість страховки на основі ціни товару.
        Логіка відновлена на основі ручного тестування користувачем.
        """
        # --- Базові фіксовані тарифи ---
        if price_usd <= 25.00:  # в этом и хуйня что сначала на сайте эта страховка стартует в диапазоне цены товара от 1$ до 25$ по 0.75$ потом в промежутке от 25$ до 51$ (получается тут уже промежуток 26$) уже 1.50$ и потом стабильно c промежутком в 25$ страховка вырастает на свои 0.75$
            return 0.75   # Рівень 1
        if price_usd <= 51.00:
            return 1.50   # Рівень 2
       # --- Для всіх цін вище $51 використовуємо єдину формулу ---
        else:
            # За основу беремо попередній поріг: $51 з ціною страховки $1.50
            base_cost_at_threshold = 1.50
            price_above_threshold = price_usd - 51.00
            
            # Розраховуємо, скільки "кроків" по $25 було зроблено
            steps = math.ceil(price_above_threshold / 25.0)
            
            # Кожен крок додає $0.75
            additional_cost = steps * 0.75
            
            return base_cost_at_threshold + additional_cost
        
class DiscountService:
    """🎁 Рассчитывает и применяет фиксированную скидку магазина."""
    DISCOUNT_PERCENTAGE = 15
    @staticmethod
    def apply_discount(price: float) -> float:
        return price * (1 - DiscountService.DISCOUNT_PERCENTAGE / 100)

class DeliveryService:
    """🚚 Рассчитывает доставку, вызывая внешние калькуляторы."""
    LBS_TO_KG = 0.453592

    @classmethod
    def calculate_international_delivery(cls, weight_lbs: float, country_code: str) -> tuple[float, str]:
        """Вызывает калькулятор Meest и возвращает стоимость и валюту."""
        weight_kg = weight_lbs * cls.LBS_TO_KG
        
        price_local = MeestDeliveryService.get_price(
            country=country_code,
            method="air",
            type_="courier",
            weight_kg=weight_kg
        )
        currency_local = MeestDeliveryService.CURRENCY[country_code]
        
        return price_local, currency_local

class MarkupService:
    """📈 Рассчитывает маржинальную наценку на товар."""
    @staticmethod
    def get_markup_percentage(price_usd: float) -> int:
        if price_usd < 20: return 30
        if price_usd < 30: return 27
        if price_usd < 40: return 25
        if price_usd < 50: return 23
        return 20

    @staticmethod
    def get_markup_adjustment(delivery_ratio: float) -> int:
        if delivery_ratio > 20: return -3
        if delivery_ratio < 10: return 3
        return 0

    @classmethod
    def calculate_final_markup(cls, price_usd: float, delivery_usd: float) -> Tuple[float, float]:
        cost_with_delivery = price_usd + delivery_usd
        base_markup = cls.get_markup_percentage(price_usd)
        delivery_ratio = (delivery_usd / cost_with_delivery) * 100 if cost_with_delivery > 0 else 0
        adjustment = cls.get_markup_adjustment(delivery_ratio)
        return base_markup + adjustment, adjustment

class RoundingService:
    """🔢 Округляет цену до красивого значения (ближайшего десятка)."""
    @staticmethod
    def round_to_nearest_ten(value: float) -> float:
        return (int(value / 10) + (1 if value % 10 != 0 else 0)) * 10

# ==================================
# 🏛️ ГЛАВНЫЙ ДОМЕННЫЙ СЕРВИС
# ==================================

class PricingService(IPricingService):
    """💸 Доменний сервіс, який виконує чистий розрахунок ціни."""

    def calculate_full_price(
        self,
        price_in_base_currency: float,
        weight_lbs: float,
        context: PricingContext,
        converter  # Об'єкт для конвертації валют
    ) -> FullPriceDetails:

        # --- 🔄 Підготовчий етап: Уніфікація компонентів у USD ---
        original_price_usd = converter.convert(price_in_base_currency, context.base_currency, "USD")
        local_delivery_usd = converter.convert(context.local_delivery_cost, context.base_currency, "USD")
        ai_commission_usd = converter.convert(context.ai_commission, context.base_currency, "USD")

        # =================================================================
        # 🟢 ПОЧАТОК ФІНАНСОВОГО КОНВЕЄРА
        # =================================================================

        # --- 🛡️ Крок 0: Розраховуємо вартість Shipping Protection від ЧИСТОЇ ціни товару ---
        protection_cost_usd = ProtectionService.get_protection_cost(original_price_usd)

        # --- 📉 Крок 1: Застосовуємо знижку магазину до суми (товар + страховка) ---
        price_before_discount = original_price_usd + protection_cost_usd
        discounted_price = DiscountService.apply_discount(price_before_discount)

        # --- 🤖 Крок 2: Додаємо сервісні збори (комісія ШІ) ---
        cost_before_delivery = discounted_price + ai_commission_usd

        # --- 🚚 Крок 3: Розраховуємо і додаємо повну вартість доставки ---
        meest_price_local, meest_currency = DeliveryService.calculate_international_delivery(
            weight_lbs, context.country_code
        )
        meest_delivery_usd = converter.convert(meest_price_local, meest_currency, "USD")
        full_delivery_usd = local_delivery_usd + meest_delivery_usd

        # --- 🧾 Крок 4: Визначаємо фінальну повну собівартість ---
        cost_price_usd = cost_before_delivery + full_delivery_usd

        # --- 📈 Крок 5: Розрахунок маржинальної націнки ---
        final_markup, markup_adjustment = MarkupService.calculate_final_markup(
            discounted_price, full_delivery_usd
        )

        # --- 💵 Крок 6: Визначення ціни продажу та прибутку ---
        sale_price_usd = cost_price_usd * (1 + final_markup / 100)
        profit_usd = sale_price_usd - cost_price_usd

        # --- 🔁 Крок 7: Округлення через UAH ---
        usd_to_uah_rate = converter.convert(1, "USD", "UAH")
        sale_price_uah = sale_price_usd * usd_to_uah_rate
        sale_price_rounded_uah = RoundingService.round_to_nearest_ten(sale_price_uah)
        sale_price_rounded_usd = sale_price_rounded_uah / usd_to_uah_rate
        profit_rounded_usd = sale_price_rounded_usd - cost_price_usd
        delta_uah = sale_price_rounded_uah - sale_price_uah

        # --- 📦 Крок 8: Повертаємо структурований результат ---
        return FullPriceDetails(
            sale_price_usd=sale_price_usd,
            sale_price_rounded_usd=sale_price_rounded_usd,
            cost_price_usd=cost_price_usd,
            profit_usd=profit_usd,
            profit_rounded_usd=profit_rounded_usd,
            full_delivery_usd=full_delivery_usd,
            markup=final_markup,
            markup_adjustment=markup_adjustment,
            weight_lbs=weight_lbs,
            round_delta_uah=delta_uah,
            protection_usd=protection_cost_usd
        )