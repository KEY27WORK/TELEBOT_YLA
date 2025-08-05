# 🔲 app/infrastructure/size_chart/generators/unique_grid_table_generator.py
"""
🔲 unique_grid_table_generator.py — Генератор сіткових таблиць (зріст × вага → розмір).

🔹 Клас `UniqueGridTableGenerator`:
    • Будує таблицю з адаптивною шириною колонок
    • Малює значення розмірів у клітинках
    • Працює з шрифтами, паддінгами, відступами, виводом у PNG
"""

# 🔠 Системні імпорти
import logging                                                     # 🧾 Логування
from typing import Dict, List                                     # 🧰 Типізація

# 🌐 Зовнішні бібліотеки
from PIL import Image, ImageDraw, ImageFont                       # 🖼️ Робота з зображенням

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME                     # 📓 Назва логера
from app.infrastructure.image_generation.font_service import FontService  # 🔤 Сервіс шрифтів
from .base_generator import BaseTableGenerator                   # 📐 Базовий генератор таблиць

logger = logging.getLogger(LOG_NAME)

# ================================
# 🔲 КЛАС: ГЕНЕРАТОР СІТКОВИХ ТАБЛИЦЬ
# ================================
class UniqueGridTableGenerator(BaseTableGenerator):
    """
    🔲 Генератор сіткових таблиць (вага/зріст → розмір).

    🔹 Підтримує дві осі: вага (горизонталь), зріст (вертикаль)
    🔹 Виводить розміри в комірках таблиці
    🔹 Автоматично масштабує ширину колонок
    """

    IMG_WIDTH = 1600												# 🖼️ Ширина зображення
    IMG_HEIGHT = 1200											# 🖼️ Висота зображення
    PADDING = 50													# 🧱 Внутрішній відступ по краях

    def __init__(self, size_chart: Dict[str, Dict[str, str]], output_path: str, font_service: FontService):
        super().__init__({}, output_path, font_service)						# 🔁 Порожній базовий size_chart — не використовується

        self.size_chart = size_chart										# 📊 Зріст → вага → розмір
        self.image = Image.new("RGB", (self.IMG_WIDTH, self.IMG_HEIGHT), "white")		# 🖼️ Білий фон зображення
        self.draw = ImageDraw.Draw(self.image)							# ✏️ Ініціалізація малювання

        self.heights = list(size_chart.keys())								# 📏 Рядки таблиці — зріст
        self.weights = list(next(iter(size_chart.values())).keys()) if size_chart else []	# ⚖️ Колонки таблиці — вага

        self.header_font = self.font_service.get_font("bold", 40)				# 🔠 Шрифт для заголовків
        self.cell_font = self.font_service.get_font("mono", 30)				# 🔡 Шрифт для комірок
        self.title_font = self.font_service.get_font("bold", 50)				# 🏷️ Шрифт заголовку таблиці

        self.row_height = 80											# 🔢 Висота рядка
        self.col_width = (self.IMG_WIDTH - 2 * self.PADDING) // (len(self.weights) + 1)	# 📐 Ширина колонки (з урахуванням лівого стовпця)
        self.table_start_y = self.PADDING + 100							# ⬇️ Відступ зверху для початку таблиці

    def draw_table(self):
        """
        📊 Виводить сіткову таблицю розмірів.
        """
        logger.info("📊 Отрисовка таблицы размеров...")

        x_start = self.PADDING										# ⬅️ Початок X
        y_start = self.table_start_y									# ⬇️ Початок Y таблиці

        self.draw_text_centered("Таблиця розмірів (см)", self.IMG_WIDTH // 2, self.PADDING, self.title_font)  # 🏷️ Заголовок

        self.draw.line(
            [(self.PADDING, y_start - 20), (self.IMG_WIDTH - self.PADDING, y_start - 20)],
            fill="black", width=3											# ➖ Лінія під заголовком
        )

        # 🔠 Заголовки ваги по горизонталі
        x_position = x_start + self.col_width
        for weight in self.weights:
            self.draw_text_centered(weight, x_position + self.col_width // 2, y_start, self.header_font)
            x_position += self.col_width									# ➡️ Наступна колонка

        y_start += self.row_height											# ⬇️ Переходимо до першого рядка

        for height in self.heights:
            x_position = x_start
            self.draw_text_centered(height, x_position + self.col_width // 2, y_start, self.header_font)	# 📏 Висота (зліва)
            x_position += self.col_width

            for weight in self.weights:
                size_value = self.size_chart[height].get(weight, "")			# 🔍 Отримуємо розмір
                self.draw_text_centered(size_value, x_position + self.col_width // 2, y_start, self.cell_font)
                self.draw.rectangle(
                    [(x_position, y_start), (x_position + self.col_width, y_start + self.row_height)],
                    outline="black", width=2									# 🧱 Малюємо межу комірки
                )
                x_position += self.col_width									# ➡️ Наступна клітинка

            y_start += self.row_height											# ⬇️ Наступний рядок

    async def generate(self) -> str:
        """
        🚀 Генерує та зберігає PNG з адаптивною сітковою таблицею.

        Returns:
            str: шлях до збереженого зображення
        """
        logger.info("🚀 Генерація сіткової таблиці...")
        self.draw_table()											# 🎨 Малюємо таблицю
        self.image.save(self.output_path, "PNG")						# 💾 Зберігаємо як PNG
        logger.info(f"✅ Таблиця успішно збережена: {self.output_path}")
        return self.output_path