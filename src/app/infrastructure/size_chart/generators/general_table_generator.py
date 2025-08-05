# 📏 app/infrastructure/size_chart/generators/general_table_generator.py
"""
📏 general_table_generator.py — Генератор класичних таблиць (розмір → параметри).

🔹 Клас `GeneralTableGenerator`:
- Створює сітку значень на білому фоні
- Відображає заголовок, розміри та параметри
- Центрує таблицю по зображенню
"""

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME                      # 🧾 Імʼя логгера
from .base_generator import BaseTableGenerator                    # 📐 Базовий генератор таблиць
from app.infrastructure.image_generation.font_service import FontService  # 🔤 Сервіс шрифтів

logger = logging.getLogger(LOG_NAME)


# ================================
# 📋 КЛАС: ГЕНЕРАТОР КЛАСИЧНИХ ТАБЛИЦЬ
# ================================
class GeneralTableGenerator(BaseTableGenerator):
    """
    📋 Генератор класичних таблиць (розмір → параметри).
    Створює сітку з підписами та значеннями, відцентровано на білому фоні.
    """

    TITLE_FONT_SIZE = 42											# 🔠 Розмір шрифту для заголовку
    HEADER_FONT_SIZE = 30										# 🔠 Розмір шрифту для заголовків
    CELL_FONT_SIZE = 28											# 🔢 Розмір шрифту для комірок
    ROW_HEIGHT = 60												# 📏 Висота одного рядка таблиці

    def __init__(self, size_chart: dict, output_path: str, font_service: FontService):
        """
        🔧 Ініціалізує генератор класичних таблиць з усіма параметрами.

        Args:
            size_chart (dict): 📊 Таблиця значень (розмір → параметри)
            output_path (str): 💾 Шлях до фінального PNG-файлу
            font_service (FontService): 🔤 Сервіс, який надає шрифти
        """
        super().__init__(size_chart, output_path, font_service)
        self.num_columns = len(self.size_chart.keys()) + 1							# 🔢 Кількість колонок: параметри + "Розмір"
        self.col_width = (self.IMG_WIDTH - 2 * self.PADDING) // self.num_columns		# 📐 Ширина кожної колонки
        total_table_height = (len(self.headers) + 1) * self.ROW_HEIGHT				# 📏 Загальна висота таблиці
        self.TABLE_START_Y = (self.IMG_HEIGHT - total_table_height) // 2				# 📍 Центрування таблиці по Y

        self.title_font = self.font_service.get_font("bold", self.TITLE_FONT_SIZE)			# 🔤 Шрифт заголовку
        self.header_font = self.font_service.get_font("bold", self.HEADER_FONT_SIZE)			# 🔤 Шрифт заголовків
        self.cell_font = self.font_service.get_font("mono", self.CELL_FONT_SIZE)			# 🔤 Моноширинний шрифт

    async def draw_title(self):
        """
        📝 Малює заголовок таблиці у верхній частині.
        """
        self.draw_text_centered(
            self.title,											# 🏷️ Назва таблиці з словника
            self.IMG_WIDTH // 2,								# 📍 Центр по ширині зображення
            self.TABLE_START_Y - 60,							# ⬆️ Відступ зверху перед таблицею
            self.title_font									# 🔤 Шрифт заголовку
        )

    async def draw_table(self):
        """
        🗃️ Малює основну таблицю розмірів.
        """
        y_position = self.TABLE_START_Y									# 📍 Початкова координата по Y
        x_position = self.PADDING										# 📍 Відступ зліва

        # 🔠 Заголовки колонок
        for col in range(self.num_columns):
            self.draw.rectangle(
                [x_position, y_position, x_position + self.col_width, y_position + self.ROW_HEIGHT],	# ⬛ Малюємо комірку заголовку
                outline="black", width=2
            )
            text = "Розмір" if col == 0 else list(self.size_chart.keys())[col - 1]		# 🏷️ Назва параметра або "Розмір"
            self.draw_text_centered(
                text,
                x_position + self.col_width // 2,								# 🧭 Центрування по ширині
                y_position + self.ROW_HEIGHT // 2,							# ↕️ Центрування по висоті
                self.header_font										# 🔤 Шрифт заголовків
            )
            x_position += self.col_width									# ➡️ Наступна колонка

        y_position += self.ROW_HEIGHT										# 🔽 Перехід до першого рядка з даними

        # 🔢 Рядки з даними
        for row in range(len(self.headers)):
            x_position = self.PADDING										# ↩️ Починаємо рядок спочатку
            for col in range(self.num_columns):
                self.draw.rectangle(
                    [x_position, y_position, x_position + self.col_width, y_position + self.ROW_HEIGHT],	# ⬛ Малюємо комірку
                    outline="black", width=2
                )
                text = (
                    self.headers[row] if col == 0
                    else str(self.size_chart[list(self.size_chart.keys())[col - 1]][row])
                )												# 🏷️ Значення комірки (або розмір, або параметр)
                self.draw_text_centered(
                    text,
                    x_position + self.col_width // 2,							# 🧭 Центрування по X
                    y_position + self.ROW_HEIGHT // 2,							# ↕️ Центрування по Y
                    self.cell_font										# 🔤 Шрифт значення
                )
                x_position += self.col_width									# ➡️ Наступна комірка
            y_position += self.ROW_HEIGHT										# 🔽 Наступний рядок

    async def generate(self) -> str:
        """
        🚀 Генерує зображення класичної таблиці та зберігає його у файл.

        Returns:
            str: 📁 Шлях до збереженого зображення
        """
        await self.draw_title()												# 📝 Малюємо заголовок
        await self.draw_table()											# 📊 Малюємо таблицю
        self.image.save(self.output_path, "PNG")								# 💾 Зберігаємо у PNG
        logger.info(f"✅ Таблицю збережено у {self.output_path}")					# 🧾 Логування
        return self.output_path												# 🔁 Повертаємо шлях до зображення
