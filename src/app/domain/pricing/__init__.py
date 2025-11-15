# 💸 app/domain/pricing/__init__.py
"""
💸 Пакет `domain.pricing` публікує контракти, DTO, утиліти та сервіс для ціноутворення.

🔹 `interfaces.py` — Money, PriceInput/PriceBreakdown, PricingContext/FullPriceDetails, IPriceService, IPricingService.
🔹 `rounding.py` — утиліти `q2` і `percent` для роботи з Decimal.
🔹 `services.py` — `PricingService` (реалізація IPriceService).
"""

# 🧩 Внутрішні модулі проєкту
from .interfaces import (                                   # 🧱 DTO та контракти
    Money,
    PriceInput,
    PriceBreakdown,
    PricingContext,
    FullPriceDetails,
    IPriceService,
    IPricingService,
)
from .rounding import q2, percent                           # ➗ Утиліти округлення та відсотків
from .services import PricingService                        # 💼 Чистий сервіс розрахунку


# ================================
# 📤 ПУБЛІЧНИЙ API ПАКЕТА
# ================================
__all__ = [
    # DTO / типи
    "Money",
    "PriceInput",
    "PriceBreakdown",
    "PricingContext",
    "FullPriceDetails",
    # Контракти
    "IPriceService",
    "IPricingService",
    # Сервіс і правила
    "PricingService",
    "PriceService",
    # Утиліти
    "q2",
    "percent",
]

# Для сумісності зі старими імпортами
PriceService = PricingService
