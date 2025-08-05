# 📐 app/infrastructure/size_chart/table_generator.py
"""
📐 table_generator.py — Генератор зображень таблиць розмірів для Telegram-бота.

🔹 Класи:
- `BaseTableGenerator` — Базовий клас із загальними методами
- `GeneralTableGenerator` — Генерація класичних таблиць (розмір → параметри)
- `UniqueTableGenerator` — Адаптивна генерація з автоматичним масштабуванням
- `UniqueGridTableGenerator` — Генерація сітки (вага × зріст → розмір)
"""

# 🔠 Системні імпорти
import logging
import asyncio
from typing import Dict, List

# 🌐 Зовнішні бібліотеки
from PIL import Image, ImageDraw, ImageFont

# 🧩 Внутрішні модулі
# ✅ (ЗМІНЕНО) Імпортуємо нові залежності
from app.infrastructure.image_generation.font_service import FontService
from app.shared.utils.logger import LOG_NAME

# ✅ (ЗМІНЕНО) Використовуємо наш централізований логер
logger = logging.getLogger(LOG_NAME)


class BaseTableGenerator:
    """📏 Базовий клас для генерації зображень таблиць розмірів."""

    IMG_WIDTH = 1080
    IMG_HEIGHT = 1920
    PADDING = 20

    def __init__(self, size_chart: Dict[str, List], output_path: str, font_service: FontService):
        """
        ✅ (ЗМІНЕНО) Конструктор тепер приймає FontService через DI.
        """
        self.size_chart = size_chart.copy()
        self.output_path = output_path
        self.font_service = font_service  # Зберігаємо сервіс шрифтів
        self.title = self.size_chart.pop("Title", "Таблиця розмірів")
        self.headers = self.size_chart.pop("Розмір", [])
        self.image = Image.new("RGB", (self.IMG_WIDTH, self.IMG_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.image)

    def _draw_text_centered(self, *args, **kwargs):
        raise NotImplementedError("Метод повинен бути реалізований у підкласі.")


class GeneralTableGenerator(BaseTableGenerator):
    """📋 Генератор класичних таблиць розмірів."""

    TITLE_FONT_SIZE = 42
    HEADER_FONT_SIZE = 30
    CELL_FONT_SIZE = 28
    ROW_HEIGHT = 60

    def __init__(self, size_chart: dict, output_path: str, font_service: FontService):
        """
        ✅ (ЗМІНЕНО) Приймає та передає FontService.
        """
        super().__init__(size_chart, output_path, font_service)
        self.num_columns = len(self.size_chart.keys()) + 1
        self.col_width = (self.IMG_WIDTH - 2 * self.PADDING) // self.num_columns
        total_table_height = (len(self.headers) + 1) * self.ROW_HEIGHT
        self.TABLE_START_Y = (self.IMG_HEIGHT - total_table_height) // 2
        
        # ✅ (ЗМІНЕНО) Шрифти отримуються через FontService
        self.title_font = self.font_service.get_font("bold", self.TITLE_FONT_SIZE)
        self.header_font = self.font_service.get_font("bold", self.HEADER_FONT_SIZE)
        self.cell_font = self.font_service.get_font("mono", self.CELL_FONT_SIZE)

    def _draw_text_centered(self, text, x, y, font, fill="black"):
        """🎯 Центрує та малює текст."""
        bbox = self.draw.textbbox((x, y), text, font=font)
        text_x = x - (bbox[2] - bbox[0]) // 2
        text_y = y - (bbox[3] - bbox[1]) // 2
        self.draw.text((text_x, text_y), text, font=font, fill=fill)

    async def draw_title(self):
        """📝 Малює заголовок таблиці."""
        self._draw_text_centered(self.title, self.IMG_WIDTH // 2, self.TABLE_START_Y - 60, self.title_font)

    async def draw_table(self):
        """🗃️ Малює основну таблицю розмірів."""
        y_position = self.TABLE_START_Y
        # Заголовки стовпців
        x_position = self.PADDING
        for col in range(self.num_columns):
            self.draw.rectangle(
                [x_position, y_position, x_position + self.col_width, y_position + self.ROW_HEIGHT],
                outline="black", width=2
            )
            text = "Розмір" if col == 0 else list(self.size_chart.keys())[col - 1]
            self._draw_text_centered(text, x_position + self.col_width // 2, y_position + self.ROW_HEIGHT // 2, self.header_font)
            x_position += self.col_width

        y_position += self.ROW_HEIGHT

        # Рядки з даними
        for row in range(len(self.headers)):
            x_position = self.PADDING
            for col in range(self.num_columns):
                self.draw.rectangle(
                    [x_position, y_position, x_position + self.col_width, y_position + self.ROW_HEIGHT],
                    outline="black", width=2
                )
                text = self.headers[row] if col == 0 else str(self.size_chart[list(self.size_chart.keys())[col - 1]][row])
                self._draw_text_centered(text, x_position + self.col_width // 2, y_position + self.ROW_HEIGHT // 2, self.cell_font)
                x_position += self.col_width
            y_position += self.ROW_HEIGHT

    async def generate(self):
        """🚀 Генерує і зберігає таблицю."""
        await self.draw_title()
        await self.draw_table()
        self.image.save(self.output_path, "PNG")
        logging.info(f"✅ Таблицю збережено у {self.output_path}")
        return self.output_path


class UniqueTableGenerator(BaseTableGenerator):
    """🖌️ Генератор адаптивних таблиць."""

    def __init__(self, size_chart: dict, output_path: str, font_service: FontService):
        """
        ✅ (ЗМІНЕНО) Приймає та передає FontService.
        """
        super().__init__(size_chart, output_path, font_service)
        if not self.headers:
            logger.warning("⚠️ Поле 'Розмір' пусте! Використовуються стандартні розміри.")
            self.headers = ["S", "M", "L", "XL", "XXL"]
        self.base_font_size = 38
        self.param_cell_font = self.font_service.get_font("bold", self.base_font_size)

    def get_max_param_width(self, extra_padding=50):
        """Определяет максимальную ширину первой колонки на основе самого длинного параметра."""
        max_width = max(
            self.draw.textlength(param, font=self.param_cell_font) for param in self.size_chart.keys()
        )
        return max_width + extra_padding  # Добавляем дополнительный отступ

    def adjust_column_spacing(self, num_sizes, first_col_width, min_width=60, min_spacing=10):
        """Автоматически рассчитывает ширину колонок и расстояние между ними."""
        total_width = self.IMG_WIDTH - (2 * self.PADDING)  # Общая ширина доступного пространства
        remaining_width = total_width - first_col_width  # Оставшееся пространство после первой колонки
        num_gaps = num_sizes - 1  # Количество промежутков между колонками

        column_width = (remaining_width - num_gaps * min_spacing) // num_sizes  # Вычисляем ширину колонки
        spacing = min_spacing if column_width >= min_width else (remaining_width - num_sizes * min_width) // num_gaps
        column_width = max(column_width, min_width)  # Убедимся, что ширина колонки не меньше минимальной

        return column_width, spacing  # Возвращаем ширину колонок и промежутки между ними
    
    async def generate(self):
        """Генерирует и сохраняет адаптивную таблицу размеров."""
        logger.info("🎨 Генерація адаптивної таблиці розмірів...")
        
        await self._calculate_layout(len(self.size_chart))  # Рассчитываем макет таблицы
        await self._draw_title()  # Отрисовываем заголовок
        await self._draw_separator_line()  # Рисуем разделительную линию
        await self._draw_headers()  # Рисуем заголовки столбцов
        await self._draw_rows(self.size_chart)  # Заполняем таблицу значениями
        await self._save_image()  # Сохраняем изображение

        return self.output_path  # Возвращаем путь к сохраненному изображению

    async def _calculate_layout(self, num_parameters):
        """Рассчитывает параметры макета таблицы."""
        max_table_width = self.IMG_WIDTH - 2 * self.PADDING  # Максимальная ширина таблицы
        max_table_height = self.IMG_HEIGHT - 2 * self.PADDING  # Максимальная высота таблицы
        
        self.first_col_width = max(self.get_max_param_width(), 250)  # Вычисляем ширину первой колонки
        self.other_col_width, self.column_spacing = self.adjust_column_spacing(len(self.headers), self.first_col_width)
        self.cell_height = 80  # Высота ячейки
        self.title_font_size = 50  # Размер шрифта заголовка
        self.padding = 20  # Внутренний отступ
        
        actual_table_width = (
            self.first_col_width + len(self.headers) * self.other_col_width + (len(self.headers) - 1) * self.column_spacing
        )
        actual_table_height = (num_parameters + 1) * self.cell_height + self.title_font_size + self.padding * 3
    
        scale_factor = min(1.0, max_table_width / actual_table_width, max_table_height / actual_table_height)  # Определяем коэффициент масштабирования
        if actual_table_width > max_table_width or actual_table_height > max_table_height:
            scale_factor = min(0.85, max_table_width / actual_table_width, max_table_height / actual_table_height)  # Ограничиваем макс. масштаб

        logger.info(f"📏 max_table_width: {max_table_width}, actual_table_width: {actual_table_width}")
        logger.info(f"📏 max_table_height: {max_table_height}, actual_table_height: {actual_table_height}")
        logger.info(f"🔍 Scale Factor (Before Fix): {scale_factor}")


        logger.info(f"🔍 Scale Factor: {scale_factor}")
        
        # ✅ (ЗМІНЕНО) Використовуємо FontService, видаляємо хардкод
        self.param_cell_font = self.font_service.get_font("bold", int(self.base_font_size * scale_factor))
        self.header_font = self.font_service.get_font("bold", int(44 * scale_factor))
        self.value_cell_font = self.font_service.get_font("mono", int(32 * scale_factor))
        self.title_font = self.font_service.get_font("bold", int(self.title_font_size * scale_factor))
        
        self.cell_height = int(self.cell_height * scale_factor)
        self.other_col_width, self.column_spacing = self.adjust_column_spacing(len(self.headers), self.first_col_width)
        self.table_height = (num_parameters + 1) * self.cell_height + self.title_font_size + self.padding * 3
        self.table_y = (self.IMG_HEIGHT - self.table_height) // 2
        self.table_start_x = max((self.IMG_WIDTH - actual_table_width) // 2, self.PADDING)

    async def _draw_title(self):
        """Отрисовывает заголовок таблицы по центру."""
        # Вычисляем позицию X для центрирования заголовка
        title_x = (self.IMG_WIDTH - self.draw.textlength(self.title, font=self.title_font)) // 2
        # Отрисовываем заголовок таблицы с небольшим отступом вверх (-20)
        self.draw.text((title_x, self.table_y - 10), self.title, font=self.title_font, fill="black")

    async def _draw_separator_line(self):
        """Рисует разделительную линию после заголовка."""
        # Определяем Y-координату для линии (чуть ниже заголовка)
        self.line_y = self.table_y + self.title_font_size + 10
        # Рисуем линию от одного края таблицы до другого с толщиной 4 пикселя
        self.draw.line([(self.PADDING, self.line_y), (self.IMG_WIDTH - self.PADDING, self.line_y)], fill="black", width=4)

    async def _draw_headers(self):
        """Отрисовывает заголовки столбцов таблицы по центру."""
        # Устанавливаем позицию Y для заголовков (чуть ниже линии, с небольшим смещением вверх)
        y_position = self.line_y + (self.cell_height - self.header_font.size) // 3
        # Устанавливаем начальную X-позицию (учитываем ширину первой колонки)
        x_position = self.table_start_x + self.first_col_width - self.column_spacing * 2

        for header in self.headers:
            # Вычисляем X-позицию для центрирования текста заголовка внутри колонки
            text_x = x_position + (self.other_col_width - self.draw.textlength(header, font=self.header_font)) // 2
            # Отрисовываем текст заголовка
            self.draw.text((text_x, y_position), header, font=self.header_font, fill="black")
            # Смещаемся к следующему столбцу (учитывая ширину столбца и отступ)
            x_position += self.other_col_width + self.column_spacing

        # Определяем начальную Y-позицию для строк таблицы (немного уменьшаем отступ)
        self.rows_start_y = self.line_y + self.cell_height - 10

    async def _draw_rows(self, adjusted_parameters):
        """Отрисовывает строки таблицы с адаптивным центрированием."""
        # Устанавливаем начальную координату Y для первой строки
        y_position = self.rows_start_y

        for param, values in adjusted_parameters.items():
            # Отрисовываем название параметра в первой колонке
            x_param = self.table_start_x + self.column_spacing * 2
            self.draw.text((x_param, y_position), param, font=self.param_cell_font, fill="black")

            # Начинаем отрисовку значений параметра с учетом отступа от первой колонки
            x_value = self.table_start_x + self.first_col_width - self.column_spacing * 2

            for value in values:
                # Вычисляем X-позицию для центрирования значения в колонке
                text_x = x_value + (self.other_col_width - self.draw.textlength(str(value), font=self.value_cell_font)) // 2
                # Отрисовываем значение
                self.draw.text((text_x, y_position + 5), str(value), font=self.value_cell_font, fill="black")
                # Смещаемся вправо к следующему значению
                x_value += self.other_col_width + self.column_spacing

            # Переходим к следующей строке (уменьшаем отступ между строками на 5 пикселей)
            y_position += self.cell_height - 5 

    async def _save_image(self):
        """Сохраняет изображение таблицы в файл."""
        self.image.save(self.output_path, "PNG")
        logger.info(f"✅ Таблиця успішно збережена в {self.output_path}")


class UniqueGridTableGenerator(BaseTableGenerator):
    """🔲 Генератор сіткових таблиць (вага/зріст → розмір)."""
    IMG_WIDTH = 1600
    IMG_HEIGHT = 1200
    PADDING = 50

    def __init__(self, size_chart: Dict[str, Dict[str, str]], output_path: str, font_service: FontService):
        # ✅ (ЗМІНЕНО) Використовуємо кастомний __init__ з BaseTableGenerator
        super().__init__({}, output_path, font_service) # Передаємо порожній словник, бо логіка інша
        self.size_chart = size_chart
        self.image = Image.new("RGB", (self.IMG_WIDTH, self.IMG_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.image)
        
        self.heights = list(size_chart.keys())
        self.weights = list(next(iter(size_chart.values())).keys()) if size_chart else []
        
        self.header_font = self.font_service.get_font("bold", 40)
        self.cell_font = self.font_service.get_font("mono", 30)
        self.title_font = self.font_service.get_font("bold", 50)

        self.row_height = 80
        self.col_width = (self.IMG_WIDTH - 2 * self.PADDING) // (len(self.weights) + 1)
        self.table_start_y = self.PADDING + 100

    def draw_text_centered(self, text, x, y, font, fill="black"):
        """Рисует центрированный текст."""
        bbox = self.draw.textbbox((x, y), text, font=font)
        text_x = x - (bbox[2] - bbox[0]) // 2
        text_y = y - (bbox[3] - bbox[1]) // 2
        self.draw.text((text_x, text_y), text, font=font, fill=fill)

    def draw_table(self):
        """Отрисовывает таблицу размеров."""
        logger.info("📊 Отрисовка таблицы размеров...")
        
        x_start = self.PADDING
        y_start = self.table_start_y

        # Заголовок таблицы
        self.draw_text_centered("Таблиця розмірів (см)", self.IMG_WIDTH // 2, self.PADDING, self.title_font)
        
        # Линия-разделитель
        self.draw.line([(self.PADDING, y_start - 20), (self.IMG_WIDTH - self.PADDING, y_start - 20)], fill="black", width=3)

        # Отрисовка заголовков столбцов (веса)
        x_position = x_start + self.col_width
        for weight in self.weights:
            self.draw_text_centered(weight, x_position + self.col_width // 2, y_start, self.header_font)
            x_position += self.col_width

        y_start += self.row_height

        # Отрисовка строк таблицы
        for height in self.heights:
            x_position = x_start
            self.draw_text_centered(height, x_position + self.col_width // 2, y_start, self.header_font)
            x_position += self.col_width

            for weight in self.weights:
                size_value = self.size_chart[height].get(weight, "")
                self.draw_text_centered(size_value, x_position + self.col_width // 2, y_start, self.cell_font)
                self.draw.rectangle([(x_position, y_start), (x_position + self.col_width, y_start + self.row_height)], outline="black", width=2)
                x_position += self.col_width

            y_start += self.row_height

    async def generate(self):
        """
        ✅ (ЗМІНЕНО) Метод тепер асинхронний для консистентності.
        """
        logger.info("🚀 Генерація сіткової таблиці...")
        # Малювання є CPU-bound, тому не потребує await всередині
        self.draw_table()
        self.image.save(self.output_path, "PNG")
        logger.info(f"✅ Таблиця успішно збережена: {self.output_path}")
        return self.output_path
