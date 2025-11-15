# 🧮 app/infrastructure/size_chart/general/__init__.py
"""
🧮 Універсальні таблиці розмірів: типи, кешування та детектор статі товару.

🔹 `ProductGender` / `GeneralChartVariant` — спільні переліки.
🔹 `YoungLAProductGenderDetector` — визначає стать продукту із HTML YoungLA.
🔹 `GeneralChartCache` — керує готовими PNG для універсальних таблиць.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки — відсутні

# 🔠 Системні імпорти — відсутні

# 🧩 Внутрішні модулі проєкту
from .cache_service import GeneralChartCache												# 💾 Кеш PNG для men/women
from .gender_detector import ProductGender, YoungLAProductGenderDetector					# 🚻 Визначення статі товару
from .types import GeneralChartVariant													# 🏷️ Перелік універсальних таблиць

__all__ = [
    "GeneralChartCache",																	# 💾 Кешування PNG
    "GeneralChartVariant",																	# 🏷️ Тип універсальної таблиці
    "ProductGender",																		# 🚻 Детермінована стать товару
    "YoungLAProductGenderDetector",														# 🧠 Детектор за HTML
]
