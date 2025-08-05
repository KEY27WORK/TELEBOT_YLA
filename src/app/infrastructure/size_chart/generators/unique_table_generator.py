# 🖌️ app/infrastructure/size_chart/generators/unique_table_generator.py

"""
🖌️ unique_table_generator.py — Генератор адаптивних таблиць розмірів.

🔹 Клас `UniqueTableGenerator`:
- Масштабує шрифти залежно від вмісту
- Центрує таблицю на полотні
- Автоматично підлаштовується під кількість параметрів і ширину
- Використовує TableGeometryService для геометрії й FontService для стилю
"""

# 🔠 Системні імпорти
import logging                                                                  # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME                                    # 📓 Назва логгера
from app.infrastructure.size_chart.services import TableGeometryService         # 📐 Сервіс геометрії
from app.infrastructure.image_generation.font_service import FontService        # 🔤 Сервіс шрифтів для генератора
from .base_generator import BaseTableGenerator                                  # 🧱 Базовий клас генератора

logger = logging.getLogger(LOG_NAME)


# =============================
# 🖌️ КЛАС: ГЕНЕРАТОР АДАПТИВНИХ ТАБЛИЦЬ
# =============================
class UniqueTableGenerator(BaseTableGenerator):
    """
    🖌️ Генератор адаптивних таблиць розмірів з автоматичним масштабуванням і центрованим виводом.
    Підлаштовується під кількість параметрів і ширину тексту.
    """

    def __init__(self, size_chart: dict, output_path: str, font_service: FontService):
        """
        🔧 Ініціалізує генератор з адаптивною розміткою.

        Args:
            size_chart (dict): 📊 Таблиця (параметр → [значення])
            output_path (str): 💾 Шлях до фінального PNG-файлу
            font_service (FontService): 🔤 Сервіс, який надає шрифти
        """
        super().__init__(size_chart, output_path, font_service)

        if not self.headers:
            logger.warning("⚠️ Поле 'Розмір' пусте! Використовуються стандартні розміри.")
            self.headers = ["S", "M", "L", "XL", "XXL"]

        self.base_font_size = 38									# 🔤 Базовий розмір шрифту
        self.param_cell_font = self.font_service.get_font("bold", self.base_font_size)	# 🔤 Шрифт параметрів (ліва колонка)

    def get_max_param_width(self, extra_padding=50):
        """
        📏 Визначає максимальну ширину першої колонки — для найширшого тексту.
        """
        max_width = max(
            self.draw.textlength(param, font=self.param_cell_font) for param in self.size_chart.keys()
        )
        return max_width + extra_padding						# ➕ Додаємо відступ

    def adjust_column_spacing(self, num_sizes, first_col_width, min_width=60, min_spacing=10):
        """
        📐 Розраховує ширину колонок і проміжки між ними.
        """
        total_width = self.IMG_WIDTH - (2 * self.PADDING)					# 🧱 Повна ширина таблиці
        remaining_width = total_width - first_col_width					# 📦 Частина після першої колонки
        num_gaps = num_sizes - 1								# 🔢 Проміжки між колонками

        column_width = (remaining_width - num_gaps * min_spacing) // num_sizes
        spacing = min_spacing if column_width >= min_width else (remaining_width - num_sizes * min_width) // num_gaps
        column_width = max(column_width, min_width)						# 🛡 Гарантуємо мінімальну ширину

        return column_width, spacing								# 🔁 Повертаємо ширину і відступ

    async def generate(self):
        """
        🚀 Генерує таблицю, малює всі елементи й зберігає зображення.
        """
        logger.info("🎨 Генерація адаптивної таблиці розмірів...")

        await self._calculate_layout(len(self.size_chart))		    # 📐 Розрахунок геометрії
        await self._draw_title()								    # 📝 Заголовок
        await self._draw_separator_line()							# 📏 Роздільна лінія
        await self._draw_headers()								    # 🔠 Заголовки розмірів
        await self._draw_rows(self.size_chart)						# 📊 Рядки параметрів і значень
        await self._save_image()								    # 💾 Збереження PNG

        return self.output_path								        # 📎 Повертаємо шлях

    async def _calculate_layout(self, num_parameters):
        """
        📐 Розраховує позиції, розміри та масштабування для усіх елементів таблиці.
        """
        service = TableGeometryService(self.IMG_WIDTH, self.IMG_HEIGHT, self.PADDING)		# 📐 Ініціалізація сервісу геометрії

        layout = service.calculate_layout(
            headers=self.headers,								# 🏷️ Список заголовків
            parameters=self.size_chart,							# 📋 Дані таблиці
            base_font_size=self.base_font_size,						# 🔤 Базовий шрифт
            font_service=self.font_service							# 🧩 Сервіс шрифтів
        )

        self.first_col_width = layout["first_col_width"]					# 📏 Ширина першої колонки
        self.other_col_width = layout["column_width"]						# 📐 Ширина колонок розмірів
        self.column_spacing = layout["column_spacing"]						# ↔️ Відступ між колонками
        self.cell_height = layout["cell_height"]							# 🔳 Висота комірки
        self.title_font_size = layout["title_font_size"]					# 🔠 Розмір заголовку
        self.padding = layout["padding_inside"]							# 📦 Padding всередині клітинки

        scale = layout["scale_factor"]								# 📏 Масштаб для шрифтів
        self.param_cell_font = self.font_service.get_font("bold", int(self.base_font_size * scale))	# 🔤 Масштабований шрифт параметрів
        self.header_font = self.font_service.get_font("bold", int(44 * scale))			# 🏷️ Заголовки
        self.value_cell_font = self.font_service.get_font("mono", int(32 * scale))			# 🔢 Значення
        self.title_font = self.font_service.get_font("bold", int(self.title_font_size))		# 🧠 Заголовок таблиці

        self.table_height = (num_parameters + 1) * self.cell_height + self.title_font_size + self.padding * 3	# 📏 Загальна висота таблиці
        self.table_y = (self.IMG_HEIGHT - self.table_height) // 2					# 📍 Центрування по Y
        self.table_start_x = max((self.IMG_WIDTH - self.IMG_WIDTH) // 2, self.PADDING)		# ◀️ Центрування по X або padding

    async def _draw_title(self):
        """
        🏷️ Виводить заголовок таблиці по центру.
        """
        title_x = (self.IMG_WIDTH - self.draw.textlength(self.title, font=self.title_font)) // 2	# 🔠 Центр по ширині
        self.draw.text((title_x, self.table_y - 10), self.title, font=self.title_font, fill="black")	# 🖋️ Малюємо заголовок

    async def _draw_separator_line(self):
        """
        ➖ Малює горизонтальну лінію після заголовка таблиці.
        """
        self.line_y = self.table_y + self.title_font_size + 10					# 🔽 Позиція нижче заголовка
        self.draw.line(
            [(self.PADDING, self.line_y), (self.IMG_WIDTH - self.PADDING, self.line_y)],
            fill="black",
            width=4
        )

    async def _draw_headers(self):
        """
        🔠 Виводить заголовки розмірів по центру стовпців.
        """
        y_position = self.line_y + (self.cell_height - self.header_font.size) // 3			# 🧭 Y-позиція
        x_position = self.table_start_x + self.first_col_width - self.column_spacing * 2		# ⬅️ Початок по X

        for header in self.headers:
            text_x = x_position + (self.other_col_width - self.draw.textlength(header, font=self.header_font)) // 2	# 🧮 Центрування
            self.draw.text((text_x, y_position), header, font=self.header_font, fill="black")		# 🖋️ Заголовок
            x_position += self.other_col_width + self.column_spacing				# 🔜 До наступного стовпця

        self.rows_start_y = self.line_y + self.cell_height - 10					# 🔽 Початок рядків

    async def _draw_rows(self, adjusted_parameters):
        """
        📋 Малює рядки таблиці з параметрами та значеннями для кожного розміру.
        """
        y_position = self.rows_start_y								# ⬇️ Стартова Y-позиція

        for param, values in adjusted_parameters.items():
            x_param = self.table_start_x + self.column_spacing * 2					# ➡️ X параметра (ліва колонка)
            self.draw.text((x_param, y_position), param, font=self.param_cell_font, fill="black")	# 🖊️ Назва параметра

            x_value = self.table_start_x + self.first_col_width - self.column_spacing * 2		# ➡️ Початок значень

            for value in values:
                text_x = x_value + (self.other_col_width - self.draw.textlength(str(value), font=self.value_cell_font)) // 2	# 🧮 Центрування
                self.draw.text((text_x, y_position + 5), str(value), font=self.value_cell_font, fill="black")	# 🖋️ Значення
                x_value += self.other_col_width + self.column_spacing				# ➡️ Наступна колонка

            y_position += self.cell_height - 5								# 🔽 Перехід до наступного рядка

    async def _save_image(self):
        """
        💾 Зберігає зображення з таблицею у PNG-файл.
        """
        self.image.save(self.output_path, "PNG")							# 💾 Збереження PNG
        logger.info(f"✅ Таблиця успішно збережена в {self.output_path}")	# 🧾 Лог про успіх