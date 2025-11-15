# 🖌️ app/infrastructure/size_chart/generators/unique_table_generator.py
"""
🖌️ `UniqueTableGenerator` — адаптивний рендер таблиці розмірів.

🔹 Використовує `TableGeometryService` для підбору ширини колонок і масштабів шрифтів.
🔹 Центрує таблицю на полотні та малює заголовок з відокремлювальною лінією.
🔹 Автоматично додає дефолтні розміри, якщо список `headers` порожній.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування генерації
from typing import Dict, List											# 📚 Типи для карт і списків

# 🧩 Внутрішні модулі проєкту
from app.domain.image_generation.interfaces import FontLike, FontType	# 🔤 Типи шрифтів
from app.infrastructure.image_generation.font_service import FontService	# 🖋️ Сервіс шрифтів
from app.infrastructure.size_chart.services import TableGeometryService	# 📐 Геометрія таблиці
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базовий логер

from .base_generator import BaseTableGenerator							# 📐 Базовий клас генераторів

logger = logging.getLogger(f"{LOG_NAME}.unique")							# 🧾 Іменований логер


# ================================
# 🖌️ ГЕНЕРАТОР АДАПТИВНИХ ТАБЛИЦЬ
# ================================
class UniqueTableGenerator(BaseTableGenerator):
    """
    🖌️ Генерує адаптивну таблицю розмірів, що підлаштовується під дані.

    Застосовує `TableGeometryService` для розрахунку ширини колонок, відступів
    та масштабів тексту, аби великі таблиці вміщалися на канві.
    """

    def __init__(
        self,
        size_chart: dict,
        output_path: str,
        font_service: FontService,
        **kwargs: object,
    ) -> None:
        """🔧 Готує дані та дефолтні значення перед рендером."""
        super().__init__(size_chart, output_path, font_service, **kwargs)	# 🧱 Параметри базового генератора

        if not self.headers:											# 🧮 Якщо розміри не передали — беремо дефолт
            logger.warning("⚠️ Поле 'Розмір' порожнє, використаємо стандартні значення.")
            self.headers = ["S", "M", "L", "XL", "XXL"]					# 📋 Дефолтний набір розмірів
        logger.debug(
            "🖌️ Ініціалізація UniqueTableGenerator: headers=%d, params=%d, output=%s",
            len(self.headers),
            len(self.parameters_map),
            self.output_path,
        )

        self.base_font_size: int = 38									# 🔢 Базовий кегль для параметрів
        self.param_cell_font: FontLike = self.font_service.get_font(	# 🔤 Початковий шрифт для параметрів
            FontType.BOLD,
            self.base_font_size,
        )

        # 🏗️ Геометрія таблиці (заповнюється під час `_calculate_layout`)
        self.first_col_width: int = 0									# 📏 Ширина першої колонки (параметри)
        self.other_col_width: int = 0									# 📏 Ширина колонок із розмірами
        self.column_spacing: int = 0									# ↔️ Відстань між колонками
        self.cell_height: int = 0										# ↕️ Висота комірки
        self.title_font_size: int = 0									# 🅰️ Розмір шрифту заголовка
        self.padding_inside: int = 0									# 🔲 Внутрішні відступи всередині клітинок

        # 🔤 Кешуємо використовувані шрифти (перераховуються після геометрії)
        self.header_font: FontLike = self.param_cell_font				# 🅱️ Шрифт для назв колонок
        self.value_cell_font: FontLike = self.param_cell_font			# 🅲 Шрифт для значень у клітинках
        self.title_font: FontLike = self.param_cell_font					# 🅰️ Шрифт заголовка

        # 📐 Координати та розміри для малювання
        self.table_height: int = 0										# 📏 Повна висота таблиці
        self.table_y: int = 0											# 📍 Горизонтальне зміщення таблиці
        self.table_start_x: int = self.PADDING							# 📍 Старт X з урахуванням зовнішнього відступу
        self.line_y: int = 0											# ➖ Y-координата роздільної лінії
        self.rows_start_y: int = 0										# 📍 Точка старту рядків даних

    async def generate(self) -> str:
        """🎨 Повний сценарій відмальовки таблиці та збереження PNG."""
        logger.info("🎨 Генерація адаптивної таблиці розмірів…")			# 🪵 Старт логу
        self._calculate_layout(len(self.parameters_map))				# 📐 Підготовка геометрії та шрифтів
        self._draw_title()												# 🖌️ Малюємо заголовок
        self._draw_separator_line()										# ➖ Відокремлюємо шапку від тіла
        self._draw_headers()											# 📋 Підписуємо колонки
        self._draw_rows(self.parameters_map)							# 📦 Виводимо параметри та значення
        logger.info("✅ Таблицю успішно збережено: %s", self.output_path)	# 🪵 Фіксуємо завершення
        return self.save_png()											# 💾 Зберігаємо та повертаємо шлях

    # ================================
    # 📐 ГЕОМЕТРІЯ ТА ПІДГОТОВКА ШРИФТІВ
    # ================================
    def _calculate_layout(self, num_parameters: int) -> None:
        """📐 Вираховуємо геометрію таблиці та оновлюємо шрифти."""
        service = TableGeometryService(self.IMG_WIDTH, self.IMG_HEIGHT, self.PADDING)	# 🛠️ Сервіс геометрії
        layout: Dict[str, int | float] = service.calculate_layout(		# 📦 Розрахунок параметрів таблиці
            headers=self.headers,
            parameters=self.parameters_map,
            base_font_size=self.base_font_size,
            font_service=self.font_service,
        )
        logger.debug("📐 Layout raw data: %s", layout)

        self.first_col_width = int(layout["first_col_width"])			# 📏 Ширина колонки параметрів
        self.other_col_width = int(layout["column_width"])				# 📏 Ширина колонок із розмірами
        self.column_spacing = int(layout["column_spacing"])				# ↔️ Проміжок між колонками
        self.cell_height = int(layout["cell_height"])					# ↕️ Висота рядка
        self.title_font_size = int(layout["title_font_size"])			# 🅰️ Розмір шрифту заголовка
        self.padding_inside = int(layout["padding_inside"])				# 🔲 Внутрішній відступ клітинок

        scale_factor = float(layout["scale_factor"])					# 📈 Коефіцієнт масштабування шрифтів
        self.param_cell_font = self.font_service.get_font(				# 🔤 Оновлений шрифт параметрів
            FontType.BOLD,
            int(self.base_font_size * scale_factor),
        )
        self.header_font = self.font_service.get_font(					# 🔤 Шрифт шапки
            FontType.BOLD,
            int(44 * scale_factor),
        )
        self.value_cell_font = self.font_service.get_font(				# 🔤 Шрифт значень у клітинках
            FontType.MONO,
            int(32 * scale_factor),
        )
        self.title_font = self.font_service.get_font(					# 🅰️ Шрифт заголовка таблиці
            FontType.BOLD,
            self.title_font_size,
        )

        self.table_height = (											# 📏 Розраховуємо висоту таблиці
            (num_parameters + 1) * self.cell_height
            + self.title_font_size
            + self.padding_inside * 3
        )
        self.table_y = (self.IMG_HEIGHT - self.table_height) // 2		# 🎯 Центруємо по вертикалі
        self.table_start_x = self.PADDING								# 📍 Лівий відступ таблиці незмінний
        logger.debug(
            "📐 Layout normalized: first_col=%d, other_col=%d, spacing=%d, cell_h=%d, title_font=%d, padding=%d, table_h=%d, table_y=%d",
            self.first_col_width,
            self.other_col_width,
            self.column_spacing,
            self.cell_height,
            self.title_font_size,
            self.padding_inside,
            self.table_height,
            self.table_y,
        )

    # ================================
    # 🖼️ МАЛЮВАННЯ КОМПОНЕНТІВ
    # ================================
    def _draw_title(self) -> None:
        """🖌️ Малює заголовок таблиці по центру."""
        title_width = int(self.draw.textlength(self.title, font=self.title_font))	# 📏 Ширина заголовка
        title_x = (self.IMG_WIDTH - title_width) // 2					# 🎯 Центр по осі X
        logger.debug("🖌️ Малюємо заголовок '%s' @ x=%d (width=%d).", self.title, title_x, title_width)
        self.draw.text(													# 🖊️ Виводимо заголовок
            (title_x, self.table_y - 10),
            self.title,
            font=self.title_font,
            fill="black",
        )

    def _draw_separator_line(self) -> None:
        """➖ Малює горизонтальну лінію між заголовком і таблицею."""
        self.line_y = self.table_y + self.title_font_size + 10			# 📍 Позиція лінії
        logger.debug("➖ Рисуємо лінію при y=%d.", self.line_y)
        self.draw.line(													# ➖ Рисуємо розділову лінію
            [(self.PADDING, self.line_y), (self.IMG_WIDTH - self.PADDING, self.line_y)],
            fill="black",
            width=4,
        )

    def _draw_headers(self) -> None:
        """📋 Відображає заголовки колонок."""
        _, header_height = self._text_size("Hg", self.header_font)		# 📏 Висота тексту шапки
        header_y = self.line_y + (self.cell_height - header_height) // 2	# 📍 Центруємо по вертикалі

        x_cursor = self.table_start_x + self.first_col_width - self.column_spacing * 2	# ▶️ Старт для колонок
        for header in self.headers:
            header_width = int(self.draw.textlength(header, font=self.header_font))	# 📏 Ширина тексту
            header_x = x_cursor + (self.other_col_width - header_width) // 2			# 🎯 Центр колонки
            logger.debug("📋 Шапка '%s' @ x=%d (width=%d).", header, header_x, header_width)
            self.draw.text(												# 🖊️ Малюємо назву розміру
                (header_x, header_y),
                header,
                font=self.header_font,
                fill="black",
            )
            x_cursor += self.other_col_width + self.column_spacing		# ➡️ Рухаємось до наступної колонки

        self.rows_start_y = self.line_y + self.cell_height				# 📍 Старт Y-координати для рядків
        logger.debug("📍 rows_start_y=%d.", self.rows_start_y)

    def _draw_rows(self, parameters: Dict[str, List[str]]) -> None:
        """📦 Малює рядки параметрів та їх значень."""
        _, param_height = self._text_size("Hg", self.param_cell_font)	# 📏 Висота тексту параметра
        _, value_height = self._text_size("Hg", self.value_cell_font)	# 📏 Висота тексту значення

        row_y = self.rows_start_y										# 📍 Поточний рядок
        for param, values in parameters.items():
            param_x = self.table_start_x + self.column_spacing * 2		# ▶️ Ліва колонка (назва параметра)
            logger.debug("📦 Рядок параметра '%s' @ y=%d.", param, row_y)
            self.draw.text(												# 🖊️ Виводимо назву параметра
                (param_x, row_y + (self.cell_height - param_height) // 2),
                str(param),
                font=self.param_cell_font,
                fill="black",
            )

            value_x = self.table_start_x + self.first_col_width - self.column_spacing * 2	# ▶️ Початок колонок значень
            for value in values:
                rendered_value = str(value)								# 🔤 Значення, приведене до рядка
                value_width = int(self.draw.textlength(rendered_value, font=self.value_cell_font))	# 📏 Ширина тексту
                text_x = value_x + (self.other_col_width - value_width) // 2		# 🎯 Центр клітинки
                logger.debug(
                    "🔢 Значення '%s' @ x=%d (width=%d).",
                    rendered_value,
                    text_x,
                    value_width,
                )
                self.draw.text(											# 🖊️ Відображаємо значення розміру
                    (text_x, row_y + (self.cell_height - value_height) // 2),
                    rendered_value,
                    font=self.value_cell_font,
                    fill="black",
                )
                value_x += self.other_col_width + self.column_spacing	# ➡️ Наступна колонка значень

            row_y += self.cell_height									# ⬇️ Переходимо до наступного параметра
        logger.debug("✅ Малювання рядків завершено, фінальний y=%d.", row_y)
