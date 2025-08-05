"""
🧩 interfaces.py — Контракты для доменных сервисов ценообразования.
"""

# 🔠 Системные импорты
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

# ================================
# 🏛️ СТРУКТУРЫ ДАННЫХ (DTO)
# ================================

@dataclass
class PricingContext:
    """DTO с региональными настройками, которые влияют на цену."""
    local_delivery_cost: float
    ai_commission: float
    base_currency: str
    country_code: str

@dataclass
class FullPriceDetails:
    """DTO с полными деталями расчёта цены в базовой валюте (USD)."""
    sale_price_usd: float
    sale_price_rounded_usd: float
    cost_price_usd: float
    profit_usd: float
    profit_rounded_usd: float
    full_delivery_usd: float
    markup: float
    markup_adjustment: float
    weight_lbs: float
    round_delta_uah: float
    protection_usd: float

# ================================
# 💰 ІНТЕРФЕЙС СЕРВІСУ ЦІНОУТВОРЕННЯ
# ================================
class IPricingService(ABC):
    """
    💰 Контракт для сервісу розрахунку цін.
    Дозволяє іншим частинам програми працювати з сервісом, не знаючи його реалізації.
    """

    @abstractmethod
    def calculate_full_price(
        self,
        price_in_base_currency: float,
        weight_lbs: float,
        context: PricingContext,
        converter: Any  # Очікуємо об'єкт-конвертер
    ) -> FullPriceDetails:
        """Розраховує повну ціну товару."""
        pass