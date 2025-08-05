# 🧠 app/infrastructure/availability/availability_processing_service.py
"""
🧠 availability_processing_service.py — Обробка повної інформації про наявність товару.

🔹 Клас `AvailabilityProcessingService`:
    • Отримує шлях до товару з URL
    • Створює заголовок (назва, зображення)
    • Викликає менеджер наявності
    • Повертає зібраний об'єкт `ProcessedAvailabilityData`
"""

# 🔠 Системні імпорти
from dataclasses import dataclass                            # 🧩 Створення імутабельного DTO
from typing import Optional                                   # 📦 Тип Optional
import logging                                                # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from .availability_manager import AvailabilityManager                        # 📦 Менеджер перевірки наявності
from .dto import AvailabilityReports                                         # 📊 DTO звітів по наявності
from app.infrastructure.content.product_header_service import (
    ProductHeaderService,                                                   # 🧠 Сервіс для отримання заголовка товару
    ProductHeaderDTO                                                        # 🏷️ DTO заголовка товару
)
from app.shared.utils.url_parser_service import UrlParserService           # 🔗 Витяг шляху з URL

logger = logging.getLogger(__name__)                                       # 🧾 Ініціалізація логгера


# ================================
# 📦 DTO ДЛЯ ПОВНОЇ ІНФОРМАЦІЇ
# ================================
@dataclass(frozen=True)
class ProcessedAvailabilityData:
    """ 🧩 DTO для зібраної інформації про наявність товару. """
    header: ProductHeaderDTO                            # 🏷️ Назва, фото, посилання
    reports: AvailabilityReports                        # 📊 Звіт по наявності (US/EU/UK)


# ================================
# 🧠 СЕРВІС ОБРОБКИ НАЯВНОСТІ
# ================================
class AvailabilityProcessingService:
    """
    🧠 Сервіс, що координує збір повної інформації про наявність.
    """

    def __init__(
        self,
        manager: AvailabilityManager,
        header_service: ProductHeaderService,
        url_parser_service: UrlParserService,
    ):
        self.manager = manager									# 📦 Менеджер звітів по наявності
        self.header_service = header_service							# 🧠 Сервіс заголовка (назва, фото)
        self.url_parser = url_parser_service							# 🔗 Парсер URL-шляху

    async def process(self, url: str) -> Optional[ProcessedAvailabilityData]:
        """
        🔄 Основний метод: збирає заголовок + звіт по наявності для конкретного товару.

        Args:
            url (str): 🔗 Повне посилання на товар

        Returns:
            Optional[ProcessedAvailabilityData]: 📦 Дані для подальшої відправки в бот
        """
        product_path = self.url_parser.extract_product_slug(url)				# 🔍 Витягуємо slug товару з URL
        if not product_path:
            return None											# 🚫 Якщо не вдалося — припиняємо обробку

        header = await self.header_service.create_header(product_path)			# 🏷️ Створюємо заголовок (назва + фото)
        if not header:
            return None											# 🚫 Якщо не вдалося отримати дані

        reports = await self.manager.get_availability_report(product_path)		# 📊 Отримуємо наявність по регіонах

        return ProcessedAvailabilityData(header=header, reports=reports)	# ✅ Повертаємо готову структуру
