# 🧠 app/infrastructure/content/product_header_service.py
"""
🧠 product_header_service.py — Сервіс для створення "заголовка" товару.

🔹 Клас `ProductHeaderService`:
- Завантажує базову інформацію про товар (title, зображення, URL)
- Повертає результат у вигляді DTO-обʼєкта
- Інкапсулює логіку парсингу заголовку, щоб уникнути дублювання
"""

# 🔠 Системні імпорти
import logging												# 🧾 Логування
from typing import Optional									# 🧰 Типізація
from dataclasses import dataclass								# 📦 DTO модель

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.parsers.parser_factory import ParserFactory		# 🏭 Фабрика парсерів
from app.shared.utils.url_parser_service import UrlParserService		# 🌐 Побудова URL товару
from app.shared.utils.logger import LOG_NAME					# 🧾 Імʼя логера

logger = logging.getLogger(LOG_NAME)								# 🔧 Ініціалізація логера


# ================================
# 📦 DTO-МОДЕЛЬ
# ================================
@dataclass(frozen=True)
class ProductHeaderDTO:
    """📦 DTO для базової інформації про товар (заголовок)."""
    title: str												# 🏷️ Назва товару
    image_url: Optional[str]								# 🖼️ Зображення (головне)
    product_url: str											# 🔗 Повний URL товару


# ================================
# 🧠 СЕРВІС СТВОРЕННЯ ЗАГОЛОВКА
# ================================
class ProductHeaderService:
    """
    🧠 Сервіс, який створює стандартизований заголовок товару (назва, фото, URL),
    уникаючи дублювання логіки в різних обробниках Telegram-бота.
    """

    def __init__(self, parser_factory: ParserFactory, url_parser_service: UrlParserService):
        self.parser_factory = parser_factory							# 🏭 Фабрика для створення парсерів
        self.url_parser = url_parser_service							# 🌐 Побудова URL з регіону + шляху

    async def create_header(self, product_path: str, region: str = "us") -> Optional[ProductHeaderDTO]:
        """
        🔄 Створює DTO-заголовок, завантажуючи title + image з товарної сторінки.

        Args:
            product_path (str): 🧱 Шлях до товару (без хосту)
            region (str): 🌍 Регіон (us, eu, uk)

        Returns:
            Optional[ProductHeaderDTO]: 📦 DTO-заголовок або None
        """
        url = self.url_parser.build_product_url(region, product_path)			# 🔧 Побудова повного URL
        if not url:
            logger.error(f"❌ Не вдалося побудувати URL для {region} та {product_path}")
            return None

        parser = self.parser_factory.create_product_parser(url, enable_progress=False)	# 🧠 Ініціалізація парсера без прогрес-бара
        product_info = await parser.get_product_info()					# 📥 Отримання інформації про товар

        if not product_info or "Помилка" in product_info.title:					# ❗ Якщо парсер повернув помилку або нічого
            return ProductHeaderDTO(
                title="🔗 ТОВАР", image_url=None, product_url=url			# ✅ Повертаємо дефолтний заголовок з посиланням
            )

        return ProductHeaderDTO(
            title=product_info.title.upper(),							# 🏷️ Назву — великими літерами
            image_url=product_info.image_url,							# 🖼️ Головне зображення
            product_url=url										# 🔗 Посилання на товар
        )