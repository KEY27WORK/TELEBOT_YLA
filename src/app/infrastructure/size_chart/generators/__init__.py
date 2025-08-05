# 📦 generators/__init__.py
"""
🧱 Пакет генераторів таблиць розмірів для Telegram-бота.

🔹 Містить реалізації різних типів генераторів:
    - `BaseTableGenerator` — базовий абстрактний клас
    - `GeneralTableGenerator` — класична таблиця (розмір → параметри)
    - `UniqueTableGenerator` — адаптивна таблиця з динамічними розмірами
    - `UniqueGridTableGenerator` — сіткова таблиця (зріст × вага → розмір)
"""

from .base_generator import BaseTableGenerator
from .general_table_generator import GeneralTableGenerator
from .unique_table_generator import UniqueTableGenerator
from .unique_grid_table_generator import UniqueGridTableGenerator
