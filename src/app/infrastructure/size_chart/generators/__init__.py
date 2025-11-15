# 🧱 app/infrastructure/size_chart/generators/__init__.py
"""
🧱 Генератори таблиць розмірів (PNG) для Telegram-бота.

🔹 `BaseTableGenerator` — абстрактний базовий клас.
🔹 `GeneralTableGenerator` — класична таблиця (розмір → параметри).
🔹 `UniqueTableGenerator` — адаптивна таблиця з динамічними колонками.
🔹 `UniqueGridTableGenerator` — сітка типу зріст×вага → розмір.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки — відсутні

# 🔠 Системні імпорти — відсутні

# 🧩 Внутрішні модулі проєкту
from .base_generator import BaseTableGenerator											# 🧱 Базовий клас для PNG-таблиць
from .general_table_generator import GeneralTableGenerator								# 📋 Генератор класичних таблиць
from .unique_grid_table_generator import UniqueGridTableGenerator						# 🗺️ Генератор сіток «зріст × вага»
from .unique_table_generator import UniqueTableGenerator								# 🖌️ Адаптивний генератор з геометрією

__all__ = [
    "BaseTableGenerator",																# 🧱 Базова абстракція
    "GeneralTableGenerator",															# 📋 Класичний формат
    "UniqueGridTableGenerator",															# 🗺️ Grid-таблиці
    "UniqueTableGenerator",																# 🖌️ Адаптивні таблиці
]
