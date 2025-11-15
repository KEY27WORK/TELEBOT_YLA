# 🏷️ app/infrastructure/size_chart/general/types.py
"""
🏷️ Переліки для універсальних таблиць і визначення статі товару.

🔹 `GeneralChartVariant` — men/women шаблони YoungLA.
🔹 `ProductGender` — стать конкретного товару, яку розпізнає детектор.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки — немає

# 🔠 Системні імпорти
from enum import Enum																# 🏷️ Побудова переліків

# 🧩 Внутрішні модулі проєкту — немає


# ================================
# 🏷️ ВАРІАНТИ УНІВЕРСАЛЬНИХ СІТОК
# ================================
class GeneralChartVariant(Enum):
    """🏷️ Вбудовані шаблони YoungLA: чоловічий і жіночий."""

    MEN = "men"																	# 🧔‍♂️ Чоловічі топи/джогери
    WOMEN = "women"															# 👩‍🦰 Жіноча універсальна сітка


# ================================
# 🚻 ГЕНДЕР ТОВАРУ
# ================================
class ProductGender(Enum):
    """🚻 Стать товару за детектором YoungLA."""

    MEN = "men"																# 🧔‍♂️ Чоловічий товар
    WOMEN = "women"															# 👩‍🦰 Жіночий товар
    UNKNOWN = "unknown"														# ❔ Визначити не вдалося


__all__ = ["GeneralChartVariant", "ProductGender"]							# 📦 Публічні типи
