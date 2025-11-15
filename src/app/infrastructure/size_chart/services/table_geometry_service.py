# 📐 app/infrastructure/size_chart/services/table_geometry_service.py
"""
📐 `TableGeometryService` — розрахунок геометрії адаптивної таблиці розмірів.

🔹 Працює з обмеженнями ширини/висоти зображення і повертає готовий макет.
🔹 Безпечно обробляє порожні заголовки/параметри (без ділення на нуль).
🔹 Враховує мінімальні розміри колонок та масштабує контент у межах допустимого.
🔹 Інтегрується з `IFontService` для точного виміру ширини тексту.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging
from typing import Dict, Mapping, Sequence

# 🧩 Внутрішні модулі проєкту
from app.domain.image_generation.interfaces import FontType, IFontService
from app.shared.utils.logger import LOG_NAME

logger = logging.getLogger(f"{LOG_NAME}.table_geometry")

__all__ = ["TableGeometryService"]


class TableGeometryService:
    """Сервіс обчислення макета таблиці: позиції, розміри, масштаб і шрифти."""

    # ✍️ Мінімальні та базові значення (можна тюнити)
    _MIN_FIRST_COL = 250                    # ширина колонки параметрів
    _EXTRA_PARAM_PADDING = 50               # додатковий відступ після тексту параметра
    _MIN_COLUMN_WIDTH = 60                  # мінімальна ширина колонки розміру
    _MIN_SPACING = 10                       # мінімальний проміжок між колонками
    _BASE_CELL_HEIGHT = 80                  # базова висота комірки
    _BASE_TITLE_PT = 50                     # базовий розмір заголовку (pt)
    _BASE_PADDING_INSIDE = 20               # внутрішній падінг комірки
    _SCALE_MIN = 0.5                        # не стискаємо менше 50%
    _SCALE_MAX = 0.85                       # не розтягуємо понад 85% від зображення

    def __init__(self, img_width: int, img_height: int, padding: int) -> None:
        self.img_width = int(img_width)     # 📏 Ширина зображення
        self.img_height = int(img_height)   # 📏 Висота зображення
        self.padding = int(padding)         # 📏 Зовнішній падінг з усіх боків

    def calculate_layout(
        self,
        *,
        headers: Sequence[str],
        parameters: Mapping[str, Sequence[object]],
        base_font_size: int,
        font_service: IFontService,
    ) -> Dict[str, int | float]:
        """
        Розраховує геометрію таблиці «параметр → [розміри...]».

        Args:
            headers: список назв розмірів (може бути порожнім).
            parameters: мапа параметрів та їх значень по колонках.
            base_font_size: базовий кегль шрифту (буде масштабовано).
            font_service: сервіс для вимірювання ширини тексту.

        Returns:
            Dict із ключами:
                `first_col_width`, `column_width`, `column_spacing`,
                `cell_height`, `title_font_size`, `scale_factor`, `padding_inside`.
        """
        # 🖼️ Доступна область для таблиці (рамка з урахуванням padding)
        max_table_width = self.img_width - 2 * self.padding
        max_table_height = self.img_height - 2 * self.padding
        logger.debug(
            "📐 Geometry input: img=%dx%d, padding=%d, max_table=%dx%d, headers=%d, parameters=%d",
            self.img_width,
            self.img_height,
            self.padding,
            max_table_width,
            max_table_height,
            len(headers),
            len(parameters),
        )

        # 📏 Ширина першої колонки (параметри)
        param_font = font_service.get_font(FontType.BOLD, int(base_font_size))
        max_param_text_width = (
            max(font_service.get_text_width(str(param), param_font) for param in parameters.keys())
            if parameters
            else 0
        )  # ✅ Безпечний максимум (0, якщо немає параметрів)
        first_col_width = max(self._MIN_FIRST_COL, max_param_text_width + self._EXTRA_PARAM_PADDING)
        logger.debug(
            "📏 first_col_width=%d (max_text=%d, base_font=%d).",
            first_col_width,
            max_param_text_width,
            base_font_size,
        )

        # 📐 Колонки під розміри
        num_sizes = max(1, len(headers))     # 🛡️ Не допускаємо 0, щоб уникнути ділення
        num_gaps = max(0, num_sizes - 1)     # 👣 Кількість проміжків між колонками
        remaining_width = max(0, max_table_width - first_col_width)
        spacing = self._MIN_SPACING if num_gaps > 0 else 0
        column_width = (
            (remaining_width - num_gaps * spacing) // num_sizes if num_sizes > 0 else remaining_width
        )

        # 📏 Якщо не влазить мінімальна ширина колонки — коригуємо spacing
        if column_width < self._MIN_COLUMN_WIDTH:
            column_width = self._MIN_COLUMN_WIDTH
            if num_gaps > 0:
                free_for_gaps = remaining_width - num_sizes * column_width
                spacing = max(0, free_for_gaps // num_gaps)
            else:
                spacing = 0
        logger.debug(
            "📐 Columns: num=%d, gaps=%d, column_width=%d, spacing=%d, remaining=%d",
            num_sizes,
            num_gaps,
            column_width,
            spacing,
            remaining_width,
        )

        # 🧭 Базові вертикальні величини
        cell_height = self._BASE_CELL_HEIGHT
        title_font_size = self._BASE_TITLE_PT
        padding_inside = self._BASE_PADDING_INSIDE

        # 📐 Фактичні розміри таблиці до масштабування
        actual_width = first_col_width + num_sizes * column_width + num_gaps * spacing
        rows_count = max(1, len(parameters))                                     # 🧮 Ряди параметрів (мінімум один)
        actual_height = (
            (rows_count + 1) * cell_height                                       # ➕ +1 рядок під заголовок колонок
            + title_font_size
            + padding_inside * 3
        )
        logger.debug(
            "📐 Actual size before scale: width=%d, height=%d (rows=%d).",
            actual_width,
            actual_height,
            rows_count,
        )

        # 🔍 Масштабування, щоб вміститись у зображення
        if actual_width <= 0 or actual_height <= 0:
            scale = 1.0
        else:
            scale = min(
                self._SCALE_MAX,                                                 # 🔼 Не розширюємо більше 85%
                max_table_width / actual_width if actual_width > 0 else 1.0,     # 🔽 Масштаб по ширині
                max_table_height / actual_height if actual_height > 0 else 1.0,  # 🔽 Масштаб по висоті
            )
            scale = max(self._SCALE_MIN, float(scale))                            # 🛡️ Обмежуємо мінімальний масштаб
        logger.debug("📏 Scale factor=%.3f.", scale)

        layout = {
            "first_col_width": int(first_col_width),
            "column_width": int(column_width),
            "column_spacing": int(spacing),
            "cell_height": int(cell_height * scale),
            "title_font_size": int(title_font_size * scale),
            "scale_factor": float(scale),
            "padding_inside": int(padding_inside),
        }  # 📦 Фінальний макет для генератора таблиць
        logger.debug("📦 Layout result: %s", layout)
        return layout
