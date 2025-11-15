# 🧩 app/domain/availability/__init__.py
"""
🧩 Пакет `domain.availability` містить контракти, DTO та сервіси для перевірки наявності.

🔹 `status.py` — трьохсостановий `AvailabilityStatus` + утиліти merge/combine.
🔹 `interfaces.py` — DTO `RegionStock`/`AvailabilityReport` і контракт `IAvailabilityService`.
🔹 `services.py` — чистий сервіс `AvailabilityService` + тип `SizeKey`.
🔹 `sorting_strategies.py` — ключі сортування розмірів (`default_size_sort_key`).
"""

# 🧩 Внутрішні модулі проєкту
from .status import AvailabilityStatus                           # 🎚️ Enum YES/NO/UNKNOWN з утилітами
from .interfaces import (                                        # 🧱 DTO + контракт сервісу
    RegionStock,
    AvailabilityReport,
    IAvailabilityService,
)
from .services import (                                          # ⚖️ Доменний сервіс та тип ключа
    AvailabilityService,
    SizeKey,
)
from .sorting_strategies import default_size_sort_key            # 📏 Базова стратегія сортування


# ================================
# 📤 ПУБЛІЧНИЙ API ПАКЕТА
# ================================
__all__ = [
    # Enum / Статуси
    "AvailabilityStatus",
    # DTO та контракт
    "RegionStock",
    "AvailabilityReport",
    "IAvailabilityService",
    # Сервіс та тип ключа
    "AvailabilityService",
    "SizeKey",
    # Стратегії сортування
    "default_size_sort_key",
]
