# 🏭 app/infrastructure/image_generation/table_generator_factory.py
"""
🏭 table_generator_factory.py — фабрика для створення генераторів таблиць.
"""

# 🔠 Системні імпорти
from typing import Dict, List                                          # 📦 Типи для даних таблиці

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.image_generation.font_service import FontService          # ✍️ Сервіс шрифтів

# 🖼️ Генератори таблиць
#from app.infrastructure.size_chart.generators.base_generator import BaseTableGenerator
#from app.infrastructure.size_chart.generators.general_table_generator import GeneralTableGenerator
#from app.infrastructure.size_chart.generators.unique_table_generator import UniqueTableGenerator
#from app.infrastructure.size_chart.generators.unique_grid_table_generator import UniqueGridTableGenerator
from app.infrastructure.size_chart.generators.table_generator import (
    BaseTableGenerator,
    GeneralTableGenerator,
    UniqueTableGenerator,
    UniqueGridTableGenerator
)

from app.shared.utils.prompts import ChartType                                   # 📊 Тип графіку/таблиці


# ================================
# 🏭 ФАБРИКА ГЕНЕРАТОРІВ ТАБЛИЦЬ
# ================================
class TableGeneratorFactory:
    """
    🏭 Створює екземпляри генераторів таблиць, впроваджуючи необхідні залежності.
    """

    def __init__(self, font_service: FontService):
        """
        ⚙️ Ініціалізує фабрику з інʼєкцією FontService.

        Args:
            font_service (FontService): ✍️ Сервіс для роботи зі шрифтами.
        """
        self.font_service = font_service								# ✍️ Зберігаємо залежність у фабриці

    def create_generator(self, chart_type: ChartType, data: Dict[str, List], path: str) -> BaseTableGenerator:
        """
        🧬 Створює конкретний генератор таблиць на основі типу.

        Args:
            chart_type (ChartType): 📊 Тип таблиці (унікальна чи загальна).
            data (Dict[str, List]): 📦 Вхідні дані для генерації.
            path (str): 🗂️ Шлях для збереження результату.

        Returns:
            BaseTableGenerator: 🖼️ Готовий екземпляр генератора.
        """
        if chart_type == ChartType.UNIQUE:
            return UniqueTableGenerator(data, path, self.font_service)  # 🧩 Адаптивна таблиця

        if chart_type == ChartType.UNIQUE_GRID:
            return UniqueGridTableGenerator(data, path, self.font_service)  # 🔲 Сіткова таблиця (вага × зріст)
    
        return GeneralTableGenerator(data, path, self.font_service)  # 📐 Класична таблиця
