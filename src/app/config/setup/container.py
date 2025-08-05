# 📦 app/config/setup/container.py
"""
📦 container.py — Контейнер залежностей (Dependency Injection Container).

🔹 Ініціалізує всі сервіси та обробники в правильному порядку.
🔹 "Впроваджує" необхідні залежності в конструктори об'єктів.
🔹 Надає єдину точку доступу до всіх компонентів системи.
"""

# 🧩 Внутрішні модулі проєкту
# --- 🧠 DOMAIN ---
from app.domain.availability.interfaces import IAvailabilityService
from app.domain.availability.services import AvailabilityService
from app.domain.pricing.interfaces import IPricingService
from app.domain.pricing.services import PricingService
from app.domain.products.interfaces import IProductSearchProvider
from app.domain.products.services.weight_resolver import WeightResolver

# --- 🧱 INFRASTRUCTURE ---
from app.config.config_service import ConfigService
from app.infrastructure.ai.open_ai_serv import OpenAIService
from app.infrastructure.ai.prompt_service import PromptService
from app.infrastructure.ai.translator import TranslatorService
from app.infrastructure.availability.availability_handler import AvailabilityHandler
from app.infrastructure.availability.availability_manager import AvailabilityManager
from app.infrastructure.availability.availability_processing_service import AvailabilityProcessingService
from app.infrastructure.availability.cache_service import AvailabilityCacheService
from app.infrastructure.availability.formatter import ColorSizeFormatter
from app.infrastructure.availability.report_builder import AvailabilityReportBuilder
from app.infrastructure.collection_processing.collection_processing_service import CollectionProcessingService
from app.infrastructure.content.gender_classifier import GenderClassifier
from app.infrastructure.content.hashtag_generator import HashtagGenerator
from app.infrastructure.content.product_content_service import ProductContentService
from app.infrastructure.content.product_header_service import ProductHeaderService
from app.infrastructure.currency.currency_manager import CurrencyManager
from app.infrastructure.data_storage.weight_data_service import WeightDataService
from app.infrastructure.music.music_recommendation import MusicRecommendation
from app.infrastructure.music.music_sender import MusicSender
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.infrastructure.parsers.product_search.search_resolver import ProductSearchResolver
from app.infrastructure.product_processing.product_processing_service import ProductProcessingService
from app.infrastructure.size_chart.image_downloader import ImageDownloader
from app.infrastructure.size_chart.ocr_service import OCRService
from app.infrastructure.size_chart.size_chart_service import SizeChartService
from app.infrastructure.telegram.handlers.price_calculator_handler import PriceCalculationHandler
from app.infrastructure.web.webdriver_service import WebDriverService
from app.shared.utils.url_parser_service import UrlParserService
from app.infrastructure.image_generation.font_service import FontService
from app.infrastructure.image_generation.table_generator_factory import TableGeneratorFactory


# --- 🤖 BOT ---
from app.bot.commands.core_commands_feature import CoreCommandsFeature
from app.bot.commands.currency_feature import CurrencyFeature
from app.bot.commands.main_menu_feature import MainMenuFeature
from app.bot.handlers.callback_handler import CallbackHandler
from app.bot.handlers.link_handler import LinkHandler
from app.bot.handlers.product.collection_handler import CollectionHandler
from app.bot.handlers.product.image_sender import ImageSender
from app.bot.handlers.product.product_handler import ProductHandler
from app.bot.handlers.size_chart_handler_bot import SizeChartHandlerBot
from app.bot.services.callback_registry import CallbackRegistry
from app.bot.ui.availability_messenger import AvailabilityMessenger
from app.bot.ui.message_formatter import MessageFormatter
from app.bot.ui.product_messenger import ProductMessenger
from app.bot.ui.size_chart_messenger import SizeChartMessenger


# ================================
# 📦 КЛАС-КОНТЕЙНЕР
# ================================
class Container:
    """
    📦 Контейнер залежностей для всього бота.
    Створює та зберігає всі екземпляри сервісів і обробників.
    """

    def __init__(self, config: ConfigService):
        """
        ⚙️ Ініціалізує всі компоненти системи у правильному порядку.
        """
        # ========================================
        # ⚙️ 1. БАЗОВІ СЕРВІСИ (без внутрішніх залежностей)
        # ========================================
        self.config = config
        self.webdriver_service = WebDriverService(config_service=self.config)
        self.currency_manager = CurrencyManager(config_service=self.config)
        self.openai_service = OpenAIService(config_service=self.config)
        self.prompt_service = PromptService()
        self.music_sender = MusicSender()
        self.weight_data_service = WeightDataService(config_service=self.config)
        self.url_parser_service = UrlParserService(config_service=self.config)
        self.image_downloader = ImageDownloader()
        self.image_sender = ImageSender()
        self.formatter = MessageFormatter()
        self.availability_cache = AvailabilityCacheService()
        self.color_size_formatter = ColorSizeFormatter(config_service=self.config)

        # ========================================
        # 🤖 2. СЕРВІСИ, ЩО ЗАЛЕЖАТЬ ВІД БАЗОВИХ
        # ========================================
        self.translator_service = TranslatorService(
            openai_service=self.openai_service,
            prompt_service=self.prompt_service
        )
        self.music_recommendation = MusicRecommendation(
            openai_service=self.openai_service
        )
        self.ocr_service = OCRService(
            openai_service=self.openai_service,
            prompt_service=self.prompt_service
        )

        self.font_service = FontService(config_service=self.config)
        self.table_generator_factory = TableGeneratorFactory(font_service=self.font_service)

        gender_rules = self.config.get("hashtags.gender_rules", {})
        self.gender_classifier = GenderClassifier(gender_rules=gender_rules)
        self.hashtag_generator = HashtagGenerator(
            config_service=self.config,
            openai_service=self.openai_service,
            prompt_service=self.prompt_service,
            gender_classifier=self.gender_classifier
        )

        # ========================================
        # 🧠 3. ДОМЕННІ СЕРВІСИ
        # ========================================
        pricing_service: IPricingService = PricingService()
        availability_service: IAvailabilityService = AvailabilityService()
        self.weight_resolver = WeightResolver(
            weight_data_service=self.weight_data_service,
            translator_service=self.translator_service
        )

        # ========================================
        # 🏭 4. ФАБРИКИ ТА МЕНЕДЖЕРИ
        # ========================================
        self.parser_factory = ParserFactory(
            webdriver_service=self.webdriver_service,
            translator_service=self.translator_service,
            weight_resolver=self.weight_resolver,
            config_service=self.config,
            url_parser_service=self.url_parser_service
        )
        self.availability_report_builder = AvailabilityReportBuilder(formatter=self.color_size_formatter)
        self.availability_manager = AvailabilityManager(
            availability_service=availability_service,
            parser_factory=self.parser_factory,
            cache_service=self.availability_cache,
            report_builder=self.availability_report_builder,
            config_service=self.config,
            url_parser_service=self.url_parser_service
        )
        self.search_resolver: IProductSearchProvider = ProductSearchResolver()

        # ========================================
        # 🛠️ 5. ВИСОКОРІВНЕВІ СЕРВІСИ ТА ОБРОБНИКИ
        # ========================================
        self.price_calculator = PriceCalculationHandler(
            currency_manager=self.currency_manager,
            parser_factory=self.parser_factory,
        )
        
        # ✅ (ВИПРАВЛЕНО) Створюємо ProductHeaderService перед його використанням
        self.product_header_service = ProductHeaderService(
            parser_factory=self.parser_factory,
            url_parser_service=self.url_parser_service
        )
        
        # ✅ (ВИПРАВЛЕНО) Передаємо відсутню залежність header_service
        self.availability_processing_service = AvailabilityProcessingService(
            manager=self.availability_manager,
            header_service=self.product_header_service,
            url_parser_service=self.url_parser_service
        )
        self.availability_messenger = AvailabilityMessenger()
        self.availability_handler = AvailabilityHandler(
            processing_service=self.availability_processing_service,
            messenger=self.availability_messenger
        )
        self.content_service = ProductContentService(
            translator_service=self.translator_service,
            hashtag_generator=self.hashtag_generator,
            price_handler=self.price_calculator
        )
        self.processing_service = ProductProcessingService(
            parser_factory=self.parser_factory,
            availability_handler=self.availability_handler,
            content_service=self.content_service,
            music_recommendation=self.music_recommendation,
            url_parser_service=self.url_parser_service
        )
        self.size_chart_service = SizeChartService(
            downloader=self.image_downloader,
            ocr_service=self.ocr_service,
            generator_factory=self.table_generator_factory
        )
        self.size_chart_messenger = SizeChartMessenger()
        self.size_chart_handler = SizeChartHandlerBot(
            parser_factory=self.parser_factory,
            size_chart_service=self.size_chart_service,
            messenger=self.size_chart_messenger
        )
        self.messenger = ProductMessenger(
            music_sender=self.music_sender,
            size_chart_handler=self.size_chart_handler,
            formatter=self.formatter
        )
        self.product_handler = ProductHandler(
            currency_manager=self.currency_manager,
            processing_service=self.processing_service,
            messenger=self.messenger
        )
        self.collection_processing_service = CollectionProcessingService(parser_factory=self.parser_factory)
        self.collection_handler = CollectionHandler(
            product_handler=self.product_handler,
            currency_manager=self.currency_manager,
            url_parser_service=self.url_parser_service,
            config_service=self.config,
            collection_processing_service=self.collection_processing_service
        )
        self.menu_handler = MainMenuFeature()

        # ========================================
        # 🔗 6. ФІЧІ ТА ГОЛОВНІ ОБРОБНИКИ
        # ========================================
        self.callback_registry = CallbackRegistry()
        self.features = [
            CoreCommandsFeature(registry=self.callback_registry),
            CurrencyFeature(self.currency_manager, registry=self.callback_registry),
        ]
        self.callback_handler = CallbackHandler(registry=self.callback_registry)
        self.link_handler = LinkHandler(
            currency_manager=self.currency_manager,
            product_handler=self.product_handler,
            collection_handler=self.collection_handler,
            size_chart_handler=self.size_chart_handler,
            price_calculator=self.price_calculator,
            availability_handler=self.availability_handler,
            search_resolver=self.search_resolver,
            url_parser_service=self.url_parser_service
        )
