# 📦 app/infrastructure/availability/__init__.py
"""
📦 Інфраструктурний шар перевірки наявності товарів.

🔹 Оркеструє процес перевірки (менеджер, сервіс обробки, кеш).
🔹 Форматує та будує звіти, локалізує тексти, інтегрується з Telegram.
🔹 Експортує публічні класи/функції для DI-контейнера та UI.
"""

from __future__ import annotations

# 🧭 Оркестрація
from .availability_manager import AvailabilityManager
from .availability_processing_service import (
    AvailabilityProcessingService,
    ProcessedAvailabilityData,
)

# 🤖 Telegram handler
from .availability_handler import AvailabilityHandler

# 🧠 Кеш та формування звітів
from .cache_service import AvailabilityCacheService
from .formatter import ColorSizeFormatter
from .report_builder import AvailabilityReportBuilder

# 📄 DTO та локалізація
from .availability_i18n import normalize_lang, t
from .dto import AvailabilityReports

__all__ = [
    "AvailabilityHandler",
    "AvailabilityProcessingService",
    "ProcessedAvailabilityData",
    "AvailabilityManager",
    "AvailabilityCacheService",
    "AvailabilityReportBuilder",
    "ColorSizeFormatter",
    "AvailabilityReports",
    "normalize_lang",
    "t",
]
