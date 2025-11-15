# 🧩 app/domain/availability/interfaces.py
"""
🧩 Доменно-орієнтовані контракти та DTO для сервісу перевірки наявності.

🔹 Визначає публічні типи (Color/Size/RegionCode) та звітні структури RegionStock/AvailabilityReport.
🔹 Описує чистий Protocol IAvailabilityService без мережі та кешів — лише трансформації даних.
🔹 Увімкнено докладне логування створення DTO та ініціалізації контрактів для спрощення дебагу.
"""

from __future__ import annotations                                                   # ⏳ Дозволяємо посилання на типи нижче

# 🔠 Системні імпорти
import logging                                                                       # 🧾 Єдине джерело логування
from dataclasses import dataclass, field                                             # 🧱 Створення DTO
from typing import Dict, List, Mapping, Protocol, runtime_checkable                 # 🧰 Типи та Protocol

# 🧩 Внутрішні модулі
from app.shared.utils.logger import LOG_NAME                                         # 🏷️ Глобальний префікс логера
from .status import AvailabilityStatus                                               # ✅ Enum: YES / NO / UNKNOWN


# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
MODULE_LOGGER_NAME: str = f"{LOG_NAME}.domain.availability.interfaces"               # 🏷️ Іменований префікс
logger = logging.getLogger(MODULE_LOGGER_NAME)                                       # 🧾 Модульний логер
logger.debug("🧩 availability.interfaces імпортовано")                                 # 🚀 Фіксуємо ініціалізацію


# ================================
# 🧾 ПУБЛІЧНІ ТИПИ (АЛІАСИ)
# ================================
Color = str                                                                          # 🎨 Ключ кольору в мапах
Size = str                                                                           # 📏 Позначення розміру
RegionCode = str                                                                     # 🌍 Код регіону (us/eu/uk…)
logger.debug("🎨 Типи визначено | Color=%s Size=%s RegionCode=%s", Color, Size, RegionCode)


# ================================
# 🏛️ СТРУКТУРИ ДАНИХ (DTO)
# ================================
@dataclass(frozen=True, slots=True)
class RegionStock:
    """
    DTO, що описує наявність товару в одному регіоні.
    """

    region_code: RegionCode                                                          # 🌍 Регіон, наприклад "us"
    stock_data: Mapping[Color, Mapping[Size, AvailabilityStatus]] = field(default_factory=dict)  # 🗂️ Мапа наявності

    def __post_init__(self) -> None:
        """
        Логує створення регіонального складу й кількість позицій.
        """
        color_count: int = len(self.stock_data)                                       # 🎨 Скільки кольорів охоплено
        logger.debug(                                                                 # 🧾 Діагностуємо DTO
            "📦 RegionStock створено | region=%s colors=%d",
            self.region_code,
            color_count,
        )


@dataclass(frozen=True, slots=True)
class AvailabilityReport:
    """
    DTO з підсумковим, повністю обробленим звітом про наявність.
    """

    availability_by_region: Mapping[Color, Mapping[RegionCode, List[Size]]]           # 🗺️ {color -> region -> sizes}
    all_sizes_map: Mapping[Color, List[Size]]                                         # 📋 {color -> всі можливі розміри}
    merged_stock: Mapping[Color, Mapping[Size, AvailabilityStatus]]                   # 🧩 {color -> size -> статус}

    def __post_init__(self) -> None:
        """
        Логує основні агрегати звіту для спрощення дебагу.
        """
        logger.debug(
            "📊 AvailabilityReport створено | colors=%d regions=%d",
            len(self.availability_by_region),
            sum(len(region_map) for region_map in self.availability_by_region.values()),
        )                                                                             # 🧾 Підсумок за кольорами/регіонами


# ================================
# 🏛️ ІНТЕРФЕЙС СЕРВІСУ (PROTOCOL)
# ================================
@runtime_checkable
class IAvailabilityService(Protocol):
    """
    💧 Контракт для сервісу, що відповідає за логіку перевірки наявності.
    Чистий домен: ніякого I/O, кешів, мережі — лише трансформації структур.
    """

    def create_report(self, all_regions_data: List[RegionStock]) -> AvailabilityReport:  # 🧾 Побудувати фінальний звіт
        """
        Приймає сирі дані з усіх регіонів і повертає структурований, детерміновано відсортований звіт.
        """
        ...


logger.debug("💧 IAvailabilityService protocol задекларовано")                        # 🧾 Контракт доступний


# ================================
# 📦 ПУБЛІЧНИЙ API МОДУЛЯ
# ================================
__all__ = [
    "Color",
    "Size",
    "RegionCode",
    "RegionStock",
    "AvailabilityReport",
    "IAvailabilityService",
    "AvailabilityStatus",
]                                                                                     # 🧾 Експортовані символи
logger.debug("🔓 __all__ оголошено: %s", __all__)                                     # 📣 Публічний API зафіксовано
