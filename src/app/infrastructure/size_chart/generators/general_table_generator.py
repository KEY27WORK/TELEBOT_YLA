# 📋 app/infrastructure/size_chart/generators/general_table_generator.py
"""
📋 `GeneralTableGenerator` — побудова класичної таблиці розмірів.

🔹 Формує сітку «Розмір → параметри» з прямокутників і підписів.
🔹 Підганяє шрифти під доступну ширину колонок (anti-overflow).
🔹 Відцентровує таблицю на канві та логгера результат.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування генерації
from typing import List													# 📚 Список параметрів

# 🧩 Внутрішні модулі проєкту
from app.domain.image_generation.interfaces import FontLike, FontType	# 🔤 Типи шрифтів для сервісу
from app.infrastructure.image_generation.font_service import FontService	# 🖋️ Провайдер шрифтів
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базова назва логера

from .base_generator import BaseTableGenerator							# 📐 Базовий функціонал побудови

logger = logging.getLogger(f"{LOG_NAME}.infrastructure.size_chart.general_table")	# 🧾 Локальний логер генератора


# ================================
# 📋 ГЕНЕРАТОР КЛАСИЧНИХ ТАБЛИЦЬ
# ================================
class GeneralTableGenerator(BaseTableGenerator):
    """
    📋 Генерує класичну таблицю (список розмірів та параметрів).

    Таблиця містить:
      • Першу колонку з розмірами (`headers`).
      • Додаткові колонки для параметрів (waist, chest тощо).
      • Грані прямокутників і текст, центрований по клітинці.
    """

    TITLE_FONT_SIZE: int = 42											# 🅰️ Розмір шрифту заголовка
    HEADER_FONT_SIZE: int = 30											# 🅱️ Розмір шрифту шапки
    CELL_FONT_SIZE: int = 28											# 🅲 Розмір шрифту для комірок
    ROW_HEIGHT: int = 60												# 📏 Висота рядка таблиці

    def __init__(
        self,
        size_chart: dict,
        output_path: str,
        font_service: FontService,
        **kwargs: object,
    ) -> None:
        """🔧 Ініціалізує генератор і адаптує шрифти під ширину колонок."""
        super().__init__(size_chart, output_path, font_service, **kwargs)	# 🧱 Налаштовуємо базовий каркас

        self.params: List[str] = list(self.parameters_map.keys())			# 📋 Перелік параметрів (колонки справа)
        self.num_columns: int = max(1, len(self.params) + 1)				# ➕ Додаємо колонку «Розмір»
        logger.debug(
            "📋 Ініціалізація: headers=%d, params=%d, columns=%d, output=%s",
            len(self.headers),
            len(self.params),
            self.num_columns,
            self.output_path,
        )

        content_width = self.IMG_WIDTH - 2 * self.PADDING					# 📐 Доступна ширина для таблиці
        self.col_width: int = max(1, content_width // self.num_columns)	# 📏 Ширина окремої колонки
        total_table_height = (len(self.headers) + 1) * self.ROW_HEIGHT		# 📏 Загальна висота таблиці
        centered_y = (self.IMG_HEIGHT - total_table_height) // 2			# 🎯 Центруємо по вертикалі
        self.table_start_y: int = max(self.PADDING, centered_y)			# 📍 Точка початку таблиці
        logger.debug(
            "📐 Layout: content_width=%d, col_width=%d, total_height=%d, start_y=%d",
            content_width,
            self.col_width,
            total_table_height,
            self.table_start_y,
        )

        self.title_font: FontLike = self.font_service.get_font(FontType.BOLD, self.TITLE_FONT_SIZE)		# 🅰️ Шрифт заголовка
        self.header_font: FontLike = self.font_service.get_font(FontType.BOLD, self.HEADER_FONT_SIZE)	# 🅱️ Шрифт шапки
        self.cell_font: FontLike = self.font_service.get_font(FontType.MONO, self.CELL_FONT_SIZE)		# 🅲 Моноширинний шрифт клітинок
        logger.debug(
            "🔤 Початкові шрифти: title=%s, header=%s, cell=%s",
            getattr(self.title_font, "size", "?"),
            getattr(self.header_font, "size", "?"),
            getattr(self.cell_font, "size", "?"),
        )
        self._maybe_downscale_fonts()										# 🔽 Перерахунок шрифтів, якщо місця замало

    # ================================
    # 🔧 АДАПТАЦІЯ ШРИФТІВ
    # ================================
    def _maybe_downscale_fonts(self) -> None:
        """🔽 Зменшує розмір шрифтів, якщо колонки занадто вузькі."""
        min_column_width = 90											# 📏 Мінімально комфортна ширина
        logger.debug("🔽 Перевіряємо ширину колонки: %d px (мінімум %d).", self.col_width, min_column_width)
        if self.col_width >= min_column_width:
            logger.debug("✅ Масштабування не потрібне (достатня ширина).")
            return														# ✅ Достатньо місця — нічого не змінюємо

        factor = max(0.7, self.col_width / float(min_column_width))		# 📉 Розраховуємо коефіцієнт масштабу
        logger.debug("📉 Зменшуємо шрифти: factor=%.2f.", factor)
        self.title_font = self.font_service.get_font(					# 🅰️ Перераховуємо шрифт заголовка
            FontType.BOLD,
            max(16, int(self.TITLE_FONT_SIZE * factor)),
        )
        self.header_font = self.font_service.get_font(					# 🅱️ Оновлюємо шапку
            FontType.BOLD,
            max(12, int(self.HEADER_FONT_SIZE * factor)),
        )
        self.cell_font = self.font_service.get_font(						# 🅲 Стандартні комірки
            FontType.MONO,
            max(10, int(self.CELL_FONT_SIZE * factor)),
        )
        logger.debug(
            "🔤 Нові шрифти: title=%s, header=%s, cell=%s",
            getattr(self.title_font, "size", "?"),
            getattr(self.header_font, "size", "?"),
            getattr(self.cell_font, "size", "?"),
        )

    # ================================
    # 🖼️ МАЛЮВАННЯ ТАБЛИЦІ
    # ================================
    def _draw_title(self) -> None:
        """🖌️ Відображає заголовок таблиці над сіткою."""
        title_y = self.table_start_y - 60
        logger.debug("🖌️ Малюємо заголовок '%s' у (%d, %d).", self.title, self.IMG_WIDTH // 2, title_y)
        self.draw_text_centered(										# 🖊️ Центруємо заголовок над таблицею
            self.title,
            self.IMG_WIDTH // 2,
            title_y,
            self.title_font,
        )

    def _draw_table(self) -> None:
        """🧱 Малює прямокутникову сітку з розмірами та параметрами."""
        y_cursor = self.table_start_y									# 🧭 Поточна координата рядка
        logger.debug(
            "🧱 Старт малювання таблиці: rows=%d, columns=%d, col_width=%d, start_y=%d.",
            len(self.headers),
            self.num_columns,
            self.col_width,
            y_cursor,
        )

        # 🔝 Малюємо шапку
        x_cursor = self.PADDING											# ▶️ Початковий відступ зліва
        for column_idx in range(self.num_columns):
            self.draw.rectangle(										# ▭ Рисуємо комірку шапки
                [x_cursor, y_cursor, x_cursor + self.col_width, y_cursor + self.ROW_HEIGHT],
                outline="black",
                width=2,
            )
            cell_label = "Розмір" if column_idx == 0 else self.params[column_idx - 1]	# 🏷️ Текст шапки
            logger.debug("🔝 Шапка: колонка %d label='%s', x=%d.", column_idx, cell_label, x_cursor)
            self.draw_text_centered(									# 🖊️ Виводимо підпис колонки
                cell_label,
                x_cursor + self.col_width // 2,
                y_cursor + self.ROW_HEIGHT // 2,
                self.header_font,
            )
            x_cursor += self.col_width									# ➡️ Переходимо до наступної колонки
        y_cursor += self.ROW_HEIGHT										# ⬇️ Переходимо до першого рядка даних

        # 📦 Малюємо рядки з даними
        for row_idx in range(len(self.headers)):
            x_cursor = self.PADDING										# 🔁 Починаємо зліва для нового рядка
            for column_idx in range(self.num_columns):
                self.draw.rectangle(									# ▭ Комірка з рамкою
                    [x_cursor, y_cursor, x_cursor + self.col_width, y_cursor + self.ROW_HEIGHT],
                    outline="black",
                    width=2,
                )
                if column_idx == 0:
                    cell_text = self.headers[row_idx]					# 🏷️ Колонка з розміром
                    display_label = "Розмір"
                else:
                    param_key = self.params[column_idx - 1]				# 🔑 Назва параметра
                    param_values = self._get_values(param_key)			# 📋 Список значень для параметра
                    cell_text = param_values[row_idx] if row_idx < len(param_values) else ""	# 🧮 Витягуємо значення
                    display_label = param_key
                logger.debug(
                    "📦 Рядок %d колонка %d ('%s') -> '%s'.",
                    row_idx,
                    column_idx,
                    display_label,
                    cell_text,
                )
                self.draw_text_centered(								# 🖊️ Малюємо текст у центрі клітинки
                    str(cell_text),
                    x_cursor + self.col_width // 2,
                    y_cursor + self.ROW_HEIGHT // 2,
                    self.cell_font,
                )
                x_cursor += self.col_width								# ➡️ Наступна колонка
            y_cursor += self.ROW_HEIGHT									# ⬇️ Наступний рядок
        logger.debug("✅ Сітку побудовано: фінальний y=%d.", y_cursor)

    async def generate(self) -> str:
        """🧾 Запускає рендер таблиці та повертає шлях до PNG."""
        logger.info("🚀 Починаємо генерацію таблиці: рядків=%d, колонок=%d.", len(self.headers), self.num_columns)
        self._draw_title()												# 🖌️ Малюємо заголовок
        self._draw_table()												# 🧱 Формуємо сітку
        logger.info("✅ Генерацію таблиці завершено, зберігаємо PNG %s", self.output_path)		# 🪵 Фіксуємо успіх
        return self.save_png()											# 💾 Зберігаємо та повертаємо шлях
