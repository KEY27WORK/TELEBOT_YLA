# 📦 app/infrastructure/availability/availability_manager.py
"""
📦 availability_manager.py — Керування перевіркою наявності товарів у різних регіонах.

✅ Клас `AvailabilityManager`:
    • Паралельно перевіряє доступність товару в регіонах (US, EU, UK)
    • Формує звіти та повертає їх у вигляді DTO
    • Використовує доменний сервіс для агрегації даних (чистий шар)
"""

# 🔠 Системні імпорти
import logging                                                  # 🧾 Логування
import asyncio                                                  # 🔄 Асинхронна багатопоточність
from typing import List, Dict                                   # 🧰 Типи для списків і словників

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                                     # ⚙️ Конфігурація з TTL і регіонами
from app.infrastructure.parsers.parser_factory import ParserFactory                    # 🏭 Фабрика парсерів товарів
from .formatter import ColorSizeFormatter                                               # 🎨 Форматування кольорів і розмірів
from .cache_service import AvailabilityCacheService                                     # 🗃️ Кешування звітів про наявність
from .report_builder import AvailabilityReportBuilder                                   # 📊 Побудова DTO-звітів
from .dto import AvailabilityReports                                                    # 📦 Клас DTO звіту
from app.domain.availability.interfaces import IAvailabilityService                     # 🧠 Інтерфейс доменного сервісу наявності
from app.domain.availability.services import RegionStock                                # 🌍 Структура з даними регіону
from app.shared.utils.url_parser_service import UrlParserService                        # 🔗 Побудова URL
from app.shared.utils.logger import LOG_NAME                                            # 🧾 Імʼя логгера

logger = logging.getLogger(LOG_NAME)


# ================================
# 🧠 КЛАС УПРАВЛІННЯ НАЯВНІСТЮ
# ================================
class AvailabilityManager:
    """
    🧠 Керує перевіркою наявності товарів у кількох регіонах та формує DTO-звіти.
    """

    def __init__(
        self,
        availability_service: IAvailabilityService,
        parser_factory: ParserFactory,
        cache_service: AvailabilityCacheService,
        report_builder: AvailabilityReportBuilder,
        config_service: ConfigService,
        url_parser_service: UrlParserService
    ):
        """
        🔧 Ініціалізація всіх залежностей через DI.
        """
        self.availability_service = availability_service							# 🧠 Доменний сервіс формування звітів
        self.parser_factory = parser_factory										# 🏭 Створює парсери по URL
        self.cache = cache_service													# 🗃️ Зберігає готові звіти
        self.report_builder = report_builder										# 📊 Побудова DTO на основі RegionStock
        self.config = config_service													# ⚙️ Отримує TTL, регіони тощо
        self.url_parser = url_parser_service										# 🔗 Побудова URL з product_path

        self.cache_ttl = self.config.get("availability.cache_ttl_sec", 300)			# ⏳ Термін дії кешу (секунди)
        self.regions: Dict[str, dict] = self.config.get("regions", {})				# 🌍 Регіони з конфігурації

    async def get_availability_report(self, product_path: str) -> AvailabilityReports:
        """
        🗃️ Формує повний звіт про наявність у регіонах.

        Args:
            product_path (str): Шлях до товару (без домену).

        Returns:
            AvailabilityReports: 📦 DTO з регіональними звітами
        """
        cached_report = self.cache.get(product_path, self.cache_ttl)					# 🗂️ Перевірка наявності в кеші
        if isinstance(cached_report, AvailabilityReports):
            logger.info(f"✅ Звіт для '{product_path}' взято з кешу.")
            return cached_report

        regional_stocks = await self._fetch_all_regions(product_path)				# 🌍 Дані по кожному регіону
        domain_report_dto = self.availability_service.create_report(regional_stocks)	# 🧠 Створення доменного DTO

        final_reports_dto = self.report_builder.build(
            region_results=regional_stocks,
            report_dto=domain_report_dto
        )

        self.cache.set(product_path, final_reports_dto)							# 🧾 Зберігаємо у кеш
        return final_reports_dto

    async def _fetch_all_regions(self, product_path: str) -> List[RegionStock]:
        """
        🔄 Збирає всі RegionStock по регіонах паралельно.
        """
        tasks = [self._fetch_region_data(region_code, product_path) for region_code in self.regions.keys()]	# 🔁 Асинхронний запуск по кожному регіону
        return await asyncio.gather(*tasks)  															# ⏳ Очікуємо завершення всіх задач

    async def _fetch_region_data(self, region_code: str, product_path: str) -> RegionStock:
        """
        📥 Завантажує дані про товар з конкретного регіону.

        Args:
            region_code (str): Ключ регіону (us, eu, uk)
            product_path (str): Шлях до товару (без домену)

        Returns:
            RegionStock: 📦 Дані про наявність для одного регіону
        """
        url = self.url_parser.build_product_url(region_code, product_path)				# 🔗 Генеруємо URL для регіону
        if not url:
            logger.error(f"❌ Не вдалося побудувати URL для регіону {region_code}")
            return RegionStock(region_code=region_code, stock_data={})

        try:
            parser = self.parser_factory.create_product_parser(url, enable_progress=False)		# 🧩 Створюємо парсер товару
            product_info = await parser.get_product_info()							# 🧾 Отримуємо дані з парсера
            stock_data = product_info.stock_data if product_info and product_info.title != "Помилка" else {}	# ✅ Перевірка на помилки
            return RegionStock(region_code=region_code, stock_data=stock_data)

        except Exception as e:
            logger.error(f"❌ Помилка отримання даних для регіону {region_code}: {e}")
            return RegionStock(region_code=region_code, stock_data={})