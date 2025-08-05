# 🏭 app/infrastructure/parsers/parser_factory.py
"""
🏭 parser_factory.py — Фабрика для створення парсерів.

🔹 Клас `ParserFactory`:
    • Створює екземпляри парсерів (товарів і колекцій)
    • Впроваджує всі необхідні залежності через DI
    • Інкапсулює логіку ініціалізації парсерів
"""

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                                     # ⚙️ Сервіс конфігурації
from app.domain.products.services.weight_resolver import WeightResolver                 # ⚖️ Сервіс визначення ваги
from app.infrastructure.ai.translator import TranslatorService                          # 🤖 Сервіс перекладу
from app.infrastructure.web.webdriver_service import WebDriverService                   # 🌍 Сервіс для роботи з браузером
from app.shared.utils.url_parser_service import UrlParserService                        # 🔗 Сервіс формування базових URL
from .base_parser import BaseParser                                                     # 📦 Оркестратор парсингу товарів
from .collections.universal_collection_parser import UniversalCollectionParser          # 📚 Парсер для сторінок колекцій


# ================================
# 🏛️ КЛАС ФАБРИКИ ПАРСЕРІВ
# ================================
class ParserFactory:
    """
    🏭 Фабрика, що створює парсери з усіма необхідними залежностями.
    """

    def __init__(
        self,
        webdriver_service: WebDriverService,
        translator_service: TranslatorService,
        weight_resolver: WeightResolver,
        config_service: ConfigService,
        url_parser_service: UrlParserService,
    ):
        """
        ⚙️ Ініціалізація фабрики з передачею всіх залежностей через DI.
        """
        self._webdriver_service = webdriver_service                       # 🌍 Інʼєкція браузерного сервісу
        self._translator_service = translator_service                     # 🤖 Інʼєкція перекладача
        self._weight_resolver = weight_resolver                           # ⚖️ Інʼєкція сервісу ваги
        self._config_service = config_service                             # ⚙️ Інʼєкція конфігурації
        self._url_parser_service = url_parser_service                     # 🔗 Інʼєкція сервісу побудови URL

    # ================================
    # 🏗️ СТВОРЕННЯ ПАРСЕРІВ
    # ================================

    def create_product_parser(self, url: str, enable_progress: bool = True) -> BaseParser:
        """
        🏗️ Створює парсер для сторінки одного товару.
        """
        return BaseParser(
            url=url,
            webdriver_service=self._webdriver_service,                    # 🌍 WebDriver
            translator_service=self._translator_service,                  # 🤖 Переклад описів
            config_service=self._config_service,                          # ⚙️ Конфігурація
            weight_resolver=self._weight_resolver,                        # ⚖️ Вага
            enable_progress=enable_progress,                              # ⏳ Прогрес-бар
            url_parser_service=self._url_parser_service                   # 🔗 Сервіс формування URL
        )

    def create_collection_parser(self, url: str) -> UniversalCollectionParser:
        """
        🏗️ Створює парсер для сторінки колекції.
        """
        return UniversalCollectionParser(
            url=url,
            webdriver_service=self._webdriver_service,                    # 🌍 WebDriver
            config_service=self._config_service,                          # ⚙️ Конфіг
            url_parser_service=self._url_parser_service                   # 🔗 URL Builder Service
        )
