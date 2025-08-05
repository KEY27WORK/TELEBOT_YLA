# 🧠 app/infrastructure/product_processing/product_processing_service.py
"""
🧠 product_processing_service.py — сервіс-оркестратор для обробки продукту.

🔹 Клас `ProductProcessingService`:
- Виконує повний цикл збору даних про товар: парсинг, наявність, контент, музика.
- Повертає єдиний DTO з усіма необхідними даними.
"""

# 🔠 Системні імпорти
import asyncio													        # 🔁 Для паралельного запуску запитів
import logging													        # 📝 Логування подій
from dataclasses import dataclass										# 📦 DTO-структура
from typing import Optional											    # 🔍 Опціональні типи

# 🧩 Внутрішні модулі проєкту
from app.domain.products.entities import ProductInfo							                                # 📦 Сутність продукту
from app.infrastructure.availability.availability_handler import AvailabilityHandler			                # 🌍 Обробка наявності
from app.infrastructure.content.product_content_service import ProductContentService, ProductContentDTO	        # 🧠 Контент товару
from app.infrastructure.music.music_recommendation import MusicRecommendation			                        # 🎵 Генерація музики
from app.infrastructure.parsers.parser_factory import ParserFactory				                                # 🏭 Фабрика парсерів
from app.shared.utils.logger import LOG_NAME							                                        # 📝 Імʼя логгера
from app.shared.utils.url_parser_service import UrlParserService				                                # 🔗 Робота з URL

logger = logging.getLogger(LOG_NAME)


# ================================
# 📦 DTO: РЕЗУЛЬТАТ ОБРОБКИ
# ================================
@dataclass(frozen=True)
class ProcessedProductData:
	"""DTO для всіх даних, необхідних для відображення продукту."""
	url: str																			# 🔗 Початковий URL товару
	page_source: str																	# 📄 HTML-код сторінки
	region_display: str																    # 🌍 Назва регіону
	content: ProductContentDTO															# 🧠 Агрегований контент товару
	music_text: str																		# 🎵 Список треків або пустий рядок


# ================================
# 🏛️ КЛАС СЕРВІСУ ОБРОБКИ
# ================================
class ProductProcessingService:
    def __init__(
        self,
        parser_factory: ParserFactory,
        availability_handler: AvailabilityHandler,
        content_service: ProductContentService,
        music_recommendation: MusicRecommendation,
        url_parser_service: UrlParserService,
    ):
        self.parser_factory = parser_factory										# 🏭 Фабрика парсерів товарів
        self.availability_handler = availability_handler							# 🌍 Обробка наявності товару
        self.content_service = content_service									    # 🧠 Агрегація всього контенту про товар
        self.music_recommendation = music_recommendation						    # 🎵 AI-рекомендація музики
        self.url_parser_service = url_parser_service							    # 🔗 Сервіс роботи з URL (region, slug)

    async def process_url(self, url: str) -> Optional[ProcessedProductData]:
        """
        🔁 Виконує повний цикл збору даних про товар за URL:
        1. Парсить товар
        2. Отримує slug + регіон
        3. Отримує наявність і музику (паралельно)
        4. Генерує контент
        5. Повертає результат у вигляді DTO

        Args:
            url (str): 🔗 Посилання на товар

        Returns:
            Optional[ProcessedProductData]: ✅ DTO з усіма необхідними даними або None при помилці
        """
        logger.info(f"⚙️ Починаю повну обробку URL: {url}")
        parser = self.parser_factory.create_product_parser(url)					            # 🛠️ Створення парсера
        product_info = await parser.get_product_info()							            # 📥 Отримання інформації про товар

        if not isinstance(product_info, ProductInfo) or "Помилка" in product_info.title:
            logger.error(f"❌ Не вдалося отримати базову інформацію про товар: {url}")
            return None

        product_slug = self.url_parser_service.extract_product_slug(url)				    # 🔍 Витягуємо slug для перевірки наявності
        if not product_slug:
            logger.error(f"❌ Не вдалося витягти slug з URL: {url}")
            return None

        region_display = self.url_parser_service.get_region(url)						    # 🌍 Визначаємо регіон сайту

        # ✅ Паралельні запити: наявність + музика
        availability_task = self.availability_handler.get_availability_reports(product_slug)
        music_task = self.music_recommendation.find_music(
            product_info.title,
            product_info.description,
            product_info.image_url
        )

        availability_reports = {}
        music_text = ""

        try:
            availability_reports, music_text = await asyncio.gather(availability_task, music_task)	        # ⚡ Паралельне виконання
        except Exception as e:
            logger.error(f"🔥 Помилка при паралельному запиті наявності/музики: {e}")

        colors_text = availability_reports.get("public_report", "Не вдалося отримати дані про наявність.")	# 📦 Публічний звіт про наявність

        content_data = await self.content_service.build_product_content(								# 🧠 Агрегація повного контенту (опис, ціна, зображення...)
            title=product_info.title,													# 🏷️ Назва товару
            description=product_info.description,										# 📃 Опис товару
            image_url=product_info.image_url,											# 🖼️ Перше зображення
            url=url,															        # 🔗 Посилання на товар
            colors_text=colors_text														# 🎨 Текст з кольорами і наявністю
        )

        return ProcessedProductData(
            url=url,																	# 🔗 Посилання на товар
            page_source=parser.page_source or "",										# 📄 HTML-код сторінки з парсера (може бути пустим)
            region_display=region_display,												# 🌍 Регіон сайту
            content=content_data,														# 🧠 Повний DTO-контент
            music_text=music_text														# 🎵 Рекомендована музика
        )

