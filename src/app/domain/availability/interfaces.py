 # 🧩 app/domain/availability/interfaces.py
"""
🧩 interfaces.py — Контракти (інтерфейси) та публічні структури даних (DTO)
для доменного сервісу перевірки наявності.
"""

# 🔠 Системные импорты
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict

# ==========================
# 🏛️ СТРУКТУРИ ДАНИХ (DTO)
# ==========================
@dataclass
class RegionStock:
    """DTO, що описує наявність товару в одному регіоні."""
    region_code: str
    stock_data: Dict[str, Dict[str, bool]] = field(default_factory=dict)

@dataclass
class AvailabilityReport:
    """DTO з підсумковим, повністю обробленим звітом про наявність."""
    availability_by_region: Dict[str, Dict[str, List[str]]]                 # { " цвет ": { " регион ": [ "размеры" ] } }
    all_sizes_map: Dict[str, List[str]]                                     # { " цвет ": [ "все", "размеры", "для", "этого", "цвета" ] }
    merged_stock: Dict[str, Dict[str, bool]]                                # { " цвет ": { " размер ": наличие (bool) } }

# ==============================
# 🏛️ ІНТЕРФЕЙС СЕРВІСУ
# ==============================
class IAvailabilityService(ABC):
    """
    💧 Контракт для сервісу, що відповідає за логіку перевірки наявності.
    """

    @abstractmethod
    def create_report(self, all_regions_data: List[RegionStock]) -> AvailabilityReport:
        """
        Приймає сирі дані з усіх регіонів і повертає структурований звіт.
        """
        pass
