# 🗺️ app/infrastructure/size_chart/generators/unique_grid_table_generator.py
"""
🗺️ `UniqueGridTableGenerator` — побудова сітки «зріст × вага → розмір».

🔹 Очікує словник, де ключі — зріст, а значення — мапа ваги до розміру.
🔹 Масштабує шрифти та розміри клітинок залежно від канви.
🔹 Відмальовує таблицю із заголовком, роздільною лінією та рамками.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування генерації
from typing import Dict												# 📚 Типи для сітки

# 🧩 Внутрішні модулі проєкту
from app.domain.image_generation.interfaces import FontLike, FontType	# 🔤 Типи шрифтів
from app.infrastructure.image_generation.font_service import FontService	# 🖋️ Сервіс шрифтів
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базовий логер

from .base_generator import BaseTableGenerator							# 📐 Базова логіка

logger = logging.getLogger(f"{LOG_NAME}.unique_grid")					# 🧾 Іменований логер


# ================================
# 🗺️ ГЕНЕРАТОР GRID-ТАБЛИЦЬ
# ================================
class UniqueGridTableGenerator(BaseTableGenerator):
    """
    🗺️ Формує таблицю відповідності розміру до зросту та ваги.

    Дані очікуються у форматі:
    {
        "Title": "Men Size Grid",
        "170": {"60": "S", "70": "M"},
        "175": {"60": "M", "70": "L"},
    }
    """

    _TITLE_PT: int = 50													# 🅰️ Базовий кегль заголовка
    _HEADER_PT: int = 40												# 🅱️ Шапка таблиці
    _CELL_PT: int = 30													# 🅲 Значення клітинок
    _ROW_HEIGHT: int = 80												# ↕️ Висота рядка до масштабування
    _TITLE_GAP: int = 20												# ↕️ Відступ між заголовком і лінією
    _LINE_GAP: int = 20													# ↕️ Відступ між лінією та таблицею
    _BORDER: int = 2													# ▭ Товщина рамок

    def __init__(
        self,
        size_chart: dict,
        output_path: str,
        font_service: FontService,
        **kwargs: object,
    ) -> None:
        """🔧 Підготовка даних сітки та масштабів шрифту."""
        super().__init__(size_chart, output_path, font_service, **kwargs)	# 🧱 Базові налаштування

        self.grid: Dict[str, Dict[str, str]] = {							# 🧮 Витягуємо частину «зріст → {вага: розмір}»
            key: value
            for key, value in self.size_chart.items()
            if isinstance(value, dict)
        }
        logger.debug("🗺️ Початкові ключі сітки: %s", list(self.grid.keys()))
        self.heights = list(self.grid.keys())							# 📋 Список значень зросту
        self.weights = list(next(iter(self.grid.values())).keys()) if self.grid else []	# 📋 Заголовки ваги
        if not self.grid:
            logger.warning("⚠️ Grid size_chart не містить даних (тільки %s).", list(self.size_chart.keys()))
        logger.debug(
            "📏 Сітка: heights=%d, weights=%d, output=%s",
            len(self.heights),
            len(self.weights),
            self.output_path,
        )

        scale = max(min(self.IMG_WIDTH / 1600, self.IMG_HEIGHT / 1200), 0.7)	# 📈 Масштабування від канви
        logger.debug(
            "📈 Масштабування канви: width=%d, height=%d, scale=%.2f",
            self.IMG_WIDTH,
            self.IMG_HEIGHT,
            scale,
        )

        self.title_font: FontLike = self.font_service.get_font(FontType.BOLD, int(self._TITLE_PT * scale))	# 🅰️ Шрифт заголовка
        self.header_font: FontLike = self.font_service.get_font(FontType.BOLD, int(self._HEADER_PT * scale))	# 🅱️ Шрифт шапки
        self.cell_font: FontLike = self.font_service.get_font(FontType.MONO, int(self._CELL_PT * scale))		# 🅲 Шрифт клітинок
        logger.debug(
            "🔤 Кеглі: title=%s, header=%s, cell=%s",
            getattr(self.title_font, "size", "?"),
            getattr(self.header_font, "size", "?"),
            getattr(self.cell_font, "size", "?"),
        )

        self.row_height = int(self._ROW_HEIGHT * scale)					# ↕️ Масштабована висота рядка
        self.title_gap = int(self._TITLE_GAP * scale)					# ↕️ Відступ між заголовком і лінією
        self.line_gap = int(self._LINE_GAP * scale)						# ↕️ Відступ між лінією та таблицею
        self.border = max(int(self._BORDER * scale), 1)					# ▭ Товщина рамки (мінімум 1)
        logger.debug(
            "📐 Геометрія до розрахунку: row_height=%d, title_gap=%d, line_gap=%d, border=%d",
            self.row_height,
            self.title_gap,
            self.line_gap,
            self.border,
        )

        self._calc_geometry()											# 📐 Розраховуємо координати таблиці

    # ================================
    # 📐 ПІДГОТОВКА КООРДИНАТ
    # ================================
    def _calc_geometry(self) -> None:
        """📐 Обчислює положення заголовка, лінії та таблиці."""
        available_width = self.IMG_WIDTH - 2 * self.PADDING				# 📏 Доступна ширина
        available_height = self.IMG_HEIGHT - 2 * self.PADDING			# 📏 Доступна висота

        title_size = int(getattr(self.title_font, "size", self._TITLE_PT))	# 🅰️ Поточний розмір шрифту заголовка
        title_block_height = title_size + self.title_gap + self.line_gap	# 📏 Висота блоку над таблицею
        table_height_available = max(available_height - title_block_height, self.row_height * 2)	# 📏 Місце для таблиці

        rows = max(len(self.heights) + 1, 2)								# ➕ Додаємо рядок шапки ваги
        self.cell_height = min(self.row_height, table_height_available // rows)	# ↕️ Висота клітинки

        columns = max(len(self.weights) + 1, 2)							# ➕ Додаємо колонку «Зріст»
        self.cell_width = max(60, available_width // columns)			# ↔️ Ширина клітинки

        self.title_center_y = self.PADDING + title_size // 2				# 🎯 Центр заголовка
        self.line_y = self.PADDING + title_block_height					# ➖ Позиція роздільної лінії
        self.table_x0 = self.PADDING										# 📍 Лівий верхній кут таблиці
        self.table_y0 = self.line_y + self.line_gap						# 📍 Верх таблиці + відступ
        logger.debug(
            "📐 Geometry: avail_w=%d, avail_h=%d, cell=%dx%d, title_y=%d, line_y=%d, table=(%d,%d)",
            available_width,
            available_height,
            self.cell_width,
            self.cell_height,
            self.title_center_y,
            self.line_y,
            self.table_x0,
            self.table_y0,
        )

    # ================================
    # 🖼️ МАЛЮВАННЯ СІТКИ
    # ================================
    def _draw_title_and_line(self) -> None:
        """🖌️ Відображає заголовок і горизонтальну лінію."""
        logger.debug("🖌️ Заголовок '%s' у (%d, %d).", self.title, self.IMG_WIDTH // 2, self.title_center_y)
        self.draw_text_centered(										# 🖊️ Малюємо заголовок по центру
            self.title,
            self.IMG_WIDTH // 2,
            self.title_center_y,
            self.title_font,
        )
        logger.debug("➖ Горизонтальна лінія y=%d, border=%d.", self.line_y, max(self.border, 2))
        self.draw.line(													# ➖ Горизонтальна лінія під заголовком
            [(self.PADDING, self.line_y), (self.IMG_WIDTH - self.PADDING, self.line_y)],
            fill="black",
            width=max(self.border, 2),
        )

    def _draw_headers(self) -> None:
        """📋 Малює шапку таблиці з вагами."""
        y_cursor = self.table_y0										# 📍 Рядок шапки
        x_cursor = self.table_x0										# 📍 Колонка шапки

        self._cell_border(x_cursor, y_cursor, self.cell_width, self.cell_height)	# ▭ Порожня верхня ліворуч
        logger.debug("📋 Малюємо порожню клітинку шапки (%d, %d).", x_cursor, y_cursor)
        x_cursor += self.cell_width										# ➡️ Переходимо до колонок ваги

        for weight in self.weights:
            logger.debug("📋 Шапка вага '%s' x=%d.", weight, x_cursor)
            self._cell_border(x_cursor, y_cursor, self.cell_width, self.cell_height)	# ▭ Рамка комірки
            self.draw_text_centered(									# 🖊️ Виводимо вагу
                weight,
                x_cursor + self.cell_width // 2,
                y_cursor + self.cell_height // 2,
                self.header_font,
            )
            x_cursor += self.cell_width									# ➡️ Наступна вага

    def _draw_rows(self) -> None:
        """📦 Відображає рядки зросту та значення комірок."""
        y_cursor = self.table_y0 + self.cell_height						# 📍 Починаємо з першого рядка даних
        for height in self.heights:
            logger.debug("📦 Рядок для зросту '%s' y=%d.", height, y_cursor)
            x_cursor = self.table_x0									# ◀️ Початок рядка
            self._cell_border(x_cursor, y_cursor, self.cell_width, self.cell_height)	# ▭ Клітинка «Зріст»
            self.draw_text_centered(									# 🖊️ Підписуємо зріст
                height,
                x_cursor + self.cell_width // 2,
                y_cursor + self.cell_height // 2,
                self.header_font,
            )
            x_cursor += self.cell_width									# ➡️ Переходимо до значень

            for weight in self.weights:
                self._cell_border(x_cursor, y_cursor, self.cell_width, self.cell_height)	# ▭ Рамка значення
                value = self.grid.get(height, {}).get(weight, "")		# 🔍 Значення з мапи
                logger.debug(
                    "🔢 Клітинка height=%s weight=%s -> '%s' (x=%d,y=%d).",
                    height,
                    weight,
                    value,
                    x_cursor,
                    y_cursor,
                )
                self._draw_cell_value(value, x_cursor, y_cursor)		# 🖊️ Центруємо текст у клітинці
                x_cursor += self.cell_width								# ➡️ Наступна клітинка

            y_cursor += self.cell_height									# ⬇️ Наступний рядок
        logger.debug("✅ Рядки завершено, кінцевий y=%d.", y_cursor)

    def _draw_cell_value(self, value: str, x_left: int, y_top: int) -> None:
        """🔤 Малює значення клітинки, піджимаючи шрифт при потребі."""
        text = str(value)												# 🔤 Перетворюємо на рядок
        font: FontLike = self.cell_font									# 🖋️ Базовий шрифт для значення

        while (															# ♻️ Зменшуємо шрифт, якщо текст не влазить
            self.draw.textlength(text, font=font) > self.cell_width - 10
            and int(getattr(font, "size", 0)) > 10
        ):
            next_size = max(10, int(getattr(font, "size", 16)) - 2)		# 📉 Зменшуємо кегль
            logger.debug(
                "🔽 Комірка '%s' не влазить (%d px). Зменшуємо шрифт до %d pt.",
                text,
                self.draw.textlength(text, font=font),
                next_size,
            )
            font = self.font_service.get_font(FontType.MONO, next_size)	# 🔄 Перебудовуємо шрифт

        logger.debug(
            "🔤 Клітинка '%s' малюється центром (%d,%d) шрифтом %s.",
            text,
            x_left + self.cell_width // 2,
            y_top + self.cell_height // 2,
            getattr(font, "size", "?"),
        )
        self.draw_text_centered(										# 🖊️ Виводимо фінальне значення
            text,
            x_left + self.cell_width // 2,
            y_top + self.cell_height // 2,
            font,
        )

    def _cell_border(self, x: int, y: int, w: int, h: int) -> None:
        """▭ Малює рамку прямокутної клітинки."""
        logger.debug("▭ Рамка клітинки (%d,%d) %dx%d.", x, y, w, h)
        self.draw.rectangle(											# ▭ Контур клітинки
            [(x, y), (x + w, y + h)],
            outline="black",
            width=self.border,
        )

    async def generate(self) -> str:
        """🚀 Запускає побудову сітки та повертає шлях до PNG."""
        logger.info(
            "🚀 Генерація сіткової таблиці: heights=%d, weights=%d, output=%s",
            len(self.heights),
            len(self.weights),
            self.output_path,
        )  # 🪵 Старт генерації
        self._draw_title_and_line()										# 🖌️ Малюємо заголовок
        self._draw_headers()											# 📋 Виводимо ваги у шапці
        self._draw_rows()												# 📦 Заповнюємо сітку значеннями
        logger.info("✅ Таблицю успішно збережено: %s", self.output_path)	# 🪵 Завершення
        return self.save_png()											# 💾 Зберігаємо результат
