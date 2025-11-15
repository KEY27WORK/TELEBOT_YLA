# 🏭 app/infrastructure/size_chart/table_generator_factory.py
"""
🏭 `TableGeneratorFactory` — фабрика генераторів PNG таблиць розмірів.

🔹 Створює конкретний генератор залежно від `ChartType`.
🔹 Обгортає створення генераторів, приховуючи деталі ініціалізації.
🔹 Має м’яку валідацію структури даних для зручного дебагу.
🔹 Надає константу `CHART_TYPE_PRIORITY` для стабільного сортування.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування фабрики
from typing import Any, Dict, List, Mapping, MutableMapping					# 🧰 Типізація входів

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.image_generation.font_service import FontService	# 🖋️ Робота з шрифтами
from app.infrastructure.size_chart.generators.base_generator import BaseTableGenerator	# 📐 Абстрактний генератор
from app.infrastructure.size_chart.generators.general_table_generator import GeneralTableGenerator	# 📋 Класичний генератор
from app.infrastructure.size_chart.generators.unique_grid_table_generator import UniqueGridTableGenerator	# 🗺️ Сітка зріст×вага
from app.infrastructure.size_chart.generators.unique_table_generator import UniqueTableGenerator	# 🖌️ Адаптивна таблиця
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базовий логер
from app.shared.utils.prompts import ChartType								# 🧾 Типи таблиць (доменно)

logger = logging.getLogger(f"{LOG_NAME}.factory")							# 🧾 Локальний логер фабрики


# ================================
# 🧭 ПРІОРИТЕТ ТИПІВ ТАБЛИЦЬ
# ================================
CHART_TYPE_PRIORITY: Dict[ChartType, int] = {
    ChartType.UNIQUE: 0,													# 🥇 Унікальні таблиці (адаптивні)
    ChartType.GENERAL: 1,													# 🥈 Класичні таблиці
    ChartType.UNIQUE_GRID: 2,												# 🥉 Сіткові таблиці
}

_META_KEYS = {"Title", "Розмір", "Размер"}									# 🏷️ Службові ключі, які не перевіряємо


# ================================
# 🏭 ФАБРИКА ГЕНЕРАТОРІВ
# ================================
class TableGeneratorFactory:
    """
    🏭 Створює генератори під конкретний `ChartType`.

    Використовується для побудови PNG в залежності від типу таблиці.
    """

    def __init__(
        self,
        font_service: FontService,
    ) -> None:
        self.font_service = font_service									# 🔤 Провайдер шрифтів

    # ================================
    # 🔌 ПУБЛІЧНИЙ API
    # ================================
    def create_generator(
        self,
        *,
        chart_type: ChartType,
        data: Mapping[str, Any],
        path: str,
    ) -> BaseTableGenerator:
        """
        🧩 Створює конкретний генератор таблиці.

        Args:
            chart_type: Тип таблиці (`ChartType`).
            data: Вихідні дані з OCR/ручного вводу.
            path: Шлях, куди зберігати PNG.
        """
        data_copy: MutableMapping[str, Any] = dict(data)					# 🧾 Робимо м'яку копію для валідації
        logger.info(
            "🏭 Створюємо генератор: type=%s, path=%s, ключів=%d",
            chart_type.value,
            path,
            len(data_copy),
        )

        generator_cls: type[BaseTableGenerator]

        if chart_type is ChartType.UNIQUE:								# 🖌️ Адаптивна таблиця
            generator_cls = UniqueTableGenerator
            self._validate_unique_shape(data_copy)						# ✅ М'яка валідація
        elif chart_type is ChartType.GENERAL:							# 📋 Класична таблиця
            generator_cls = GeneralTableGenerator
            self._validate_general_shape(data_copy)
        elif chart_type is ChartType.UNIQUE_GRID:						# 🗺️ Сітка (зріст×вага)
            generator_cls = UniqueGridTableGenerator
            self._validate_grid_shape(data_copy)
        else:															# 🚫 Невідомий тип
            logger.error("❌ Невідомий тип таблиці: %s", chart_type)
            raise ValueError(f"Unsupported chart_type: {chart_type!r}")

        generator = generator_cls(										# 🧱 Створюємо генератор
            size_chart=data_copy,
            output_path=path,
            font_service=self.font_service,
        )
        logger.debug("🏗️ Ініціалізовано генератор %s для %s.", generator_cls.__name__, path)
        return generator

    # ================================
    # ✅ ВАЛІДАЦІЇ ФОРМАТУ
    # ================================
    def _validate_general_shape(self, data: MutableMapping[str, Any]) -> None:
        """🧪 GENERAL: значення параметрів мають бути послідовностями."""
        problems: List[str] = []										# 🧾 Список підозрілих ключів
        for key, value in data.items():
            if key in _META_KEYS:
                continue												# 🎯 Пропускаємо службові поля
            if not self._is_sequence_like(value):						# ❓ Перевіряємо структуру значення
                problems.append(f"{key!r} -> {type(value).__name__}")
        if problems:
            logger.warning(
                "GENERAL: очікуємо списки значень. Підозрілі ключі (%d): %s",
                len(problems),
                ", ".join(problems),
            )
        else:
            logger.debug("GENERAL: усі ключі мають коректні послідовності (%d).", len(data))

    def _validate_unique_shape(self, data: MutableMapping[str, Any]) -> None:
        """🧪 UNIQUE: така ж структура, як і для GENERAL."""
        problems: List[str] = []											# 📝 Агрегуємо підозрілі ключі
        for key, value in data.items():
            if key in _META_KEYS:											# 🔖 Пропускаємо службові поля
                continue
            if not self._is_sequence_like(value):							# ❌ Значення не схоже на послідовність
                problems.append(f"{key!r} -> {type(value).__name__}")
        if problems:
            logger.warning(
                "UNIQUE: очікуємо списки значень. Підозрілі ключі (%d): %s",
                len(problems),
                ", ".join(problems),
            )
        else:
            logger.debug("UNIQUE: валідація пройдена (%d ключів).", len(data))

    def _validate_grid_shape(self, data: MutableMapping[str, Any]) -> None:
        """🧪 UNIQUE_GRID: значення мають бути словниками."""
        problems: List[str] = []											# 📝 Агрегуємо ключі з некоректною формою
        for key, value in data.items():
            if key in _META_KEYS:											# 🔖 Пропускаємо службові поля
                continue
            if not isinstance(value, dict):								# ❌ Очікуємо словник (height -> {weight: size})
                problems.append(f"{key!r} -> {type(value).__name__}")
        if problems:
            logger.warning(
                "UNIQUE_GRID: очікуємо словники для кожного рядка. Підозрілі ключі (%d): %s",
                len(problems),
                ", ".join(problems),
            )
        else:
            logger.debug("UNIQUE_GRID: структура валідна (%d рядків).", len(data))

    @staticmethod
    def _is_sequence_like(value: Any) -> bool:
        """
        🧪 Мінівалідація «чи схоже на список?».

        Повертаємо `True`, якщо значення ітероване (за винятком рядків/байтів).
        """
        if value is None:
            return False												# 🚫 Немає значення
        if isinstance(value, (str, bytes)):
            return False												# 🚫 Рядки не вважаємо колекцією
        try:
            iter(value)												# 🔁 Пробуємо отримати ітератор
            return True												# ✅ Виглядає як колекція
        except Exception:
            return False												# 🚫 Не ітерується


__all__ = ["CHART_TYPE_PRIORITY", "TableGeneratorFactory"]				# 📦 Експортовані сутності
