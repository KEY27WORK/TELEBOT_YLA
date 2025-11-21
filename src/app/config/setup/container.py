# 📦 app/config/setup/container.py
"""
📦 Контейнер залежностей Telegram-бота.

🔹 Створює сервіси в правильному порядку DI
🔹 Інкапсулює конфігурацію зовнішніх та внутрішніх клієнтів
🔹 Дає єдину точку доступу до обробників, фіч і менеджерів
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (зовнішніх залежностей у цьому модулі немає)

# 🔠 Системні імпорти
import logging                                                           # 🧾 Базові засоби логування
from decimal import Decimal, InvalidOperation                            # 🪙 Конвертація конфігурацій грошей
from typing import TYPE_CHECKING, Any, Dict, Optional, cast              # 🧮 Допоміжні типи та касти

# 🧩 Внутрішні модулі проєкту

# 🤖 Bot-фічі та хендлери
from app.bot.commands.core_commands_feature import CoreCommandsFeature   # 🧱 Базові команди бота
from app.bot.commands.currency_feature import CurrencyFeature            # 💱 Курсові команди
from app.bot.commands.main_menu_feature import MainMenuFeature           # 📋 Побудова головного меню
from app.bot.handlers.callback_handler import CallbackHandler            # 🔄 Централізований callback-хендлер
from app.bot.handlers.link_handler import LinkHandler                    # 🔗 Обробка вхідних посилань
from app.bot.handlers.price_calculator_handler import PriceCalculationHandler  # 🧮 Хендлер розрахунку ціни
from app.bot.handlers.order_handler import OrderFileHandler                   # 📂 Обробка .txt-файлів замовлень
from app.bot.handlers.product.collection_handler import CollectionHandler  # 🧺 Пакетна обробка колекцій
from app.bot.handlers.product.image_sender import ImageSender            # 🖼️ Відправка медіа
from app.bot.handlers.product.product_handler import ProductHandler      # 🛒 Бізнес-логіка товарів
from app.bot.handlers.size_chart_handler_bot import SizeChartHandlerBot  # 📏 Обробка таблиць розмірів
from app.bot.services.callback_registry import CallbackRegistry          # 📚 Реєстр callback-ів
from app.bot.ui.formatters.message_formatter import MessageFormatter     # 📝 Форматування повідомлень
from app.bot.ui.messengers.availability_messenger import AvailabilityMessenger  # ✅ Повідомлення про наявність
from app.bot.ui.messengers.product_messenger import ProductMessenger     # 📦 Повідомлення з товаром
from app.bot.ui.messengers.size_chart_messenger import SizeChartMessenger  # 📐 Повідомлення з таблицями

# ⚙️ Конфігурація
from app.config.setup.constants import CONST, AppConstants               # ⚙️ Глобальні константи

# 🏭 Доменна логіка
from app.domain.availability.services import AvailabilityService         # 📊 Доменний сервіс доступності
from app.domain.delivery.interfaces import IDeliveryService              # 🚚 Контракт сервісу доставки
from app.domain.pricing.services import PricingService, PricingConfig    # 💵 Доменне ціноутворення
from app.domain.products.interfaces import IProductSearchProvider        # 🔍 Контракт пошуку товарів
from app.domain.products.services.weight_resolver import WeightResolver  # ⚖️ Обрахунок ваги

# 🚨 Обробка помилок
from app.errors.error_handler import make_error_handler                  # 🚨 Обгортка обробки помилок
from app.errors.exception_handler_service import ExceptionHandlerService  # 🛡️ Менеджер винятків
from app.errors.strategies import HttpxErrorStrategy, OpenAIErrorStrategy, TelegramErrorStrategy  # 🧱 Набір стратегій помилок

# 🤖 Інфраструктура: AI / контент
from app.infrastructure.ai.ai_task_service import AITaskService          # 🤖 Завдання штучного інтелекту
from app.infrastructure.ai.open_ai_serv import OpenAIService             # 🧠 Клієнт OpenAI
from app.infrastructure.ai.prompt_service import PromptService           # 🗒️ Постачальник промптів
from app.infrastructure.content.alt_text_generator import AltTextGenerator  # 🖼️ Генератор ALT-тексту
from app.infrastructure.content.gender_classifier import GenderClassifier  # 🚻 Класифікація гендеру
from app.infrastructure.content.hashtag_generator import HashtagGenerator  # 🏷️ Генерація хештегів
from app.infrastructure.content.product_content_service import ProductContentService  # 📝 Збагачення контенту
from app.infrastructure.content.product_header_service import ProductHeaderService  # 📰 Заголовки товарів

# 📦 Інфраструктура: дані та сервіси
from app.infrastructure.collection_processing.collection_processing_service import CollectionProcessingService  # 🧺 Менеджер колекцій
from app.infrastructure.currency.currency_manager import CurrencyManager  # 💱 Менеджер валют
from app.infrastructure.data_storage.weight_data_service import WeightDataService  # 🗃️ Джерело даних ваги
from app.infrastructure.delivery.meest_delivery_service import MeestDeliveryService  # 🚚 Інтеграція Meest
from app.infrastructure.image_generation.font_service import FontService  # ✍️ Рендеринг шрифтів
from app.infrastructure.music.music_file_manager import MusicFileManager  # 🎧 Керування файлами музики
from app.infrastructure.music.music_recommendation import MusicRecommendation  # 🎵 Рекомендації саундтреків
from app.infrastructure.music.music_sender import MusicSender            # 📤 Відправка музики
from app.infrastructure.music.yt_downloader import YtDownloader          # ⬇️ Завантаження з YouTube
from app.infrastructure.parsers.factory_adapter import ParserFactoryAdapter  # 🔌 Адаптер фабрики парсерів
from app.infrastructure.parsers.parser_factory import ParserFactory      # 🧩 Фабрика парсерів
from app.infrastructure.services.banner_drop_service import BannerDropService      # 🪧 Banner drop
from app.infrastructure.services.product_media_preparer import ProductMediaPreparer  # 🖼️ Підготовка фото
from app.infrastructure.services.product_processing_service import ProductProcessingService  # 🛠️ Комплексна обробка товару

# 📏 Інфраструктура: доступність та size chart
from app.infrastructure.availability.availability_handler import AvailabilityHandler  # 📬 Обробка звітів доступності
from app.infrastructure.availability.availability_manager import AvailabilityManager  # 🗃️ Менеджер доступності
from app.infrastructure.availability.availability_processing_service import AvailabilityProcessingService  # 🧮 Оркестратор розрахунків доступності
from app.infrastructure.availability.cache_service import AvailabilityCacheService  # 🧊 Кеш по наявності
from app.infrastructure.availability.formatter import ColorSizeFormatter  # 🎨 Форматер кольорів та розмірів
from app.infrastructure.availability.report_builder import AvailabilityReportBuilder  # 🧱 Побудова звітів
from app.infrastructure.size_chart.image_downloader import ImageDownloader  # 🖼️ Викачування зображень
from app.infrastructure.size_chart.ocr_service import OCRService         # 👁️ Розпізнавання тексту
from app.infrastructure.size_chart.general import YoungLAProductGenderDetector  # 🚻 Детектор статі товарів YoungLA
from app.infrastructure.size_chart.size_chart_service import SizeChartService  # 📏 Побудова таблиць розмірів
from app.infrastructure.size_chart.table_generator_factory import TableGeneratorFactory  # 📊 Генератор таблиць
from app.infrastructure.size_chart.youngla_finder import YoungLASizeChartFinder  # 🧭 Пошук YoungLA таблиць

# 🔗 Інфраструктура: мережа та кеші
from app.infrastructure.url import YoungLAUrlStrategy                    # 🧭 Стратегія для брендових URL
from app.infrastructure.web.webdriver_service import WebDriverService    # 🌐 Selenium/Chrome клієнт
from app.infrastructure.web.youngla_order_service import YoungLAOrderService  # 🛒 Автоматизація кошика YoungLA
from app.shared.cache.html_lru_cache import HtmlLruCache                 # 🧊 LRU-кеш HTML/ALT
from app.shared.metrics.exporters import maybe_start_prometheus          # 📈 Bootstrap метрик
from app.shared.utils.interfaces import IUrlParsingStrategy              # 🧠 Контракт стратегій URL
from app.shared.utils.logger import LOG_NAME, init_logging_from_config   # 🧾 Конфіг логування
from app.shared.utils.url_parser_service import UrlParserService         # 🔗 Багатостратегічний парсер URL

if TYPE_CHECKING:
    from app.config.config_service import ConfigService                  # 🗂️ Тип під час перевірки

logger = logging.getLogger(LOG_NAME)                                     # 🧾 Модульний логер контейнера

# ================================
# 🛠️ ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _int_or_default(value: Any, default: int) -> int:
    """
    Повертає ціле число або запасне значення, якщо каст неможливий.
    """
    if value is None:                                                    # 🚫 Значення відсутнє
        return default                                                   # 🔁 Використовуємо запасне

    try:                                                                 # 🧪 Пробуємо привести тип
        coerced = int(value)                                             # 🔢 Результат приведення
        return coerced                                                   # ✅ Повертаємо перетворене значення
    except (TypeError, ValueError):                                      # ⚠️ Неможливо привести до int
        return default                                                   # 🔁 Повертаємо запасне значення


def _optional_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Перетворює значення на int або повертає default/None.
    """
    if value is None:                                                    # 🚫 Значення не передано
        return default                                                   # 🔁 Віддаємо стандарт

    try:                                                                 # 🧪 Тестуємо приведення
        coerced = int(value)                                             # 🔢 Приведене значення
        return coerced                                                   # ✅ Повертаємо результат
    except (TypeError, ValueError):                                      # ⚠️ Каст викликає помилку
        return default                                                   # 🔁 Fallback до default


def _coerce_gender_rules(raw: Any) -> Dict[str, list[str]]:
    """
    Нормалізує gender_rules у формат Dict[str, list[str]].
    """
    if not isinstance(raw, dict):                                        # 🚫 Очікували словник
        return {"default": []}                                           # 📦 Повертаємо дефолтну структуру

    rules: Dict[str, list[str]] = {}                                     # 📚 Порожнє сховище правил
    for key, value in raw.items():                                       # 🔄 Проходимо всі конфігурації
        normalized_key = str(key).strip()                                # 🧼 Забезпечуємо охайний ключ
        tags: list[str] = []                                             # 🗃️ Тимчасовий список тегів
        if isinstance(value, (list, tuple, set)):                        # 📋 Набір тегів
            normalized_items: list[str] = []                             # 📥 Акумулюємо валідні значення
            for entry in value:                                          # 🔁 Обробляємо кожен елемент
                entry_str = str(entry).strip()                           # ✂️ Прибираємо пробіли
                if entry_str:                                            # ✅ Пропускаємо порожні рядки
                    normalized_items.append(entry_str)                   # ➕ Зберігаємо теги
            tags = normalized_items                                      # 🔁 Фіксуємо результат
        elif isinstance(value, str):                                     # 🧵 Одинарний тег
            trimmed = value.strip()                                      # ✂️ Видаляємо пробіли
            if trimmed:                                                  # ✅ Перевіряємо непорожність
                tags = [trimmed]                                         # 📌 Перетворюємо у список
        if tags:                                                         # 🟢 Є валідні дані
            rules[normalized_key] = tags                                 # 💾 Фіксуємо нормалізоване правило
    rules.setdefault("default", [])                                      # 🧷 Гарантуємо ключ default
    return rules                                                         # 📤 Повертаємо нормалізовані правила


def bootstrap_logging() -> logging.Logger:
    """
    Зчитує конфіг логування і запускає кореневий логер.
    """
    from app.config.config_service import ConfigService                  # 🧭 Локальний імпорт для уникнення циклів

    cfg = ConfigService()                                                # ⚙️ Тимчасовий ConfigService
    node = cfg.get("logging", {}) or {}                                  # 📄 Вузол логування
    return init_logging_from_config(node)                                # 🧾 Стартуємо логер за конфігом


# ================================
# 🏛️ КОНТЕЙНЕР ЗАЛЕЖНОСТЕЙ
# ================================
class Container:
    """
    Координує ініціалізацію інфраструктурних, доменних та бот-сервісів.
    """

    # ================================
    # ⚙️ ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(self, config: ConfigService):
        self.config = config                                              # ⚙️ Джерело конфігурацій DI
        self.constants: AppConstants = CONST                              # 🧱 Глобальні константи застосунку
        logger.info("🚀 Стартуємо побудову контейнера залежностей")       # 🧾 Фіксуємо старт ініціалізації
        self._bootstrap_metrics_if_enabled()                              # 📈 Можливий запуск експорту метрик
        self._setup_error_handlers()                                      # 🛡️ Включаємо глобальні стратегії помилок
        self._setup_utility_services()                                    # 🧰 Підготовлюємо утилітарні сервіси
        self._setup_ai_and_content()                                      # 🤖 Налаштовуємо AI та контентний стек
        self._setup_domain_services()                                     # 🏭 Створюємо доменні сервіси
        self._setup_managers()                                            # 🧩 Фабрики та менеджери даних
        self._setup_high_level_services()                                 # 🚀 Обробники, месенджери й пайплайни
        self._setup_features_and_handlers()                               # 📚 Telegram-фічі та роутери
        logger.info("✅ Контейнер ініціалізовано успішно")                 # 🧾 Фіксуємо завершення складання

    # ================================
    # 📈 МЕТРИКИ ТА ЛОГИ
    # ================================
    def _bootstrap_metrics_if_enabled(self) -> None:
        """
        Стартує Prometheus-експортер, якщо це дозволено конфігурацією.
        """
        try:                                                             # 🧪 Ізолюємо збої метрик
            metrics_enabled = bool(self.config.get("metrics.enabled", True))  # ✅ Прапорець увімкнення
            if not metrics_enabled:                                      # 🚫 Метрики відключені
                logger.debug("📉 Prometheus вимкнено конфігом")          # 🧾 Документуємо стан
                return                                                   # 🔁 Пропускаємо запуск
            exporter_name = (self.config.get("metrics.exporter", "prometheus") or "prometheus").lower()  # 🏷️ Назва експортера
            if exporter_name != "prometheus":                            # 🚫 Поки підтримуємо лише Prometheus
                logger.debug("📉 Експортер %s не підтримується", exporter_name)  # 🧾 Лог пропуску
                return                                                   # 🔁 Нічого не запускаємо
            raw_port = self.config.get("metrics.prometheus.port", 9108, cast=int)  # 🔢 Налаштований порт
            port = _int_or_default(raw_port, 9108)                       # ⚙️ Нормалізуємо значення
            maybe_start_prometheus(port)                                 # 📈 Підіймаємо HTTP-експортер
            logger.info("📈 Prometheus запущено на порті %s", port)       # 🧾 Підтверджуємо запуск
        except Exception:                                                # ⚠️ Будь-яка помилка експортера
            logger.exception("⚠️ Не вдалося стартувати експортер метрик")  # 🧾 Додаємо трасування

    # ================================
    # 🛡️ ОБРОБКА ПОМИЛОК
    # ================================
    def _setup_error_handlers(self) -> None:
        """
        Конфігурує ExceptionHandlerService та похідні обробники.
        """
        strategies = [
            OpenAIErrorStrategy(),                                       # 🤖 Перехоплення винятків OpenAI
            HttpxErrorStrategy(),                                        # 🌐 HTTP-рівень
            TelegramErrorStrategy(),                                     # ✉️ Telegram Bot API
        ]                                                                # 🧱 Набір стратегій
        self.exception_handler_service = ExceptionHandlerService(strategies=strategies)  # 🛡️ Менеджер винятків
        self.error_handler = make_error_handler(self.exception_handler_service)           # 🔄 Уніфікована обгортка
        logger.debug("🛡️ ExceptionHandlerService активовано (%d стратегій)", len(strategies))  # 🧾 Діагностика

    # ================================
    # 🧰 УТИЛІТАРНІ СЕРВІСИ
    # ================================
    def _setup_utility_services(self) -> None:
        """
        Ініціалізує клієнти інфраструктури, кеші та допоміжні сервіси.
        """
        self.webdriver_service = WebDriverService(config_service=self.config)             # 🌐 Selenium/Chrome клієнт
        self.youngla_order_service = YoungLAOrderService(config_service=self.config)      # 🛒 Автоматизоване додавання до кошика
        self.currency_manager = CurrencyManager(config_service=self.config)               # 💱 Робота з курсами валют
        strategy_chain: list[IUrlParsingStrategy] = [
            YoungLAUrlStrategy(self.config),                                             # 🧭 Брендова стратегія YoungLA
        ]                                                                                # 🧱 Ланцюжок стратегій URL
        self.url_parser_service = UrlParserService(strategies=strategy_chain)            # 🔗 Нормалізація посилань
        default_lang = self.config.get("default_language", "uk", str) or "uk"            # 🗣️ Мова UI за змовчуванням
        self.openai_service = OpenAIService(config_service=self.config)                  # 🧠 Клієнт OpenAI
        self.prompt_service = PromptService(cfg=self.config, default_lang=default_lang)  # 🗒️ Постачальник промптів
        alt_cache_ttl = _int_or_default(self.config.get("alt_text.cache.ttl_sec", 86400, cast=int), 86400)  # ⏱️ TTL ALT-кешу
        alt_cache_max = _int_or_default(self.config.get("alt_text.cache.max_entries", 2048, cast=int), 2048)  # 📦 Розмір ALT-кешу
        self.alt_text_cache = HtmlLruCache(max_entries=alt_cache_max, ttl_sec=alt_cache_ttl)  # 🧊 LRU-кеш ALT
        alt_concurrency = _int_or_default(self.config.get("alt_text.concurrency", 2, cast=int), 2)  # 🚦 Ліміт паралельності ALT
        self.alt_text_generator = AltTextGenerator(
            openai_service=self.openai_service,
            prompt_service=self.prompt_service,
            cache=self.alt_text_cache,
            max_concurrency=alt_concurrency,
        )                                                                                # 🖼️ Генерація ALT-текстів
        self.music_file_manager = MusicFileManager(config=self.config)                   # 🎧 Робота з аудіо-файлами
        self.music_downloader = YtDownloader(config=self.config)                         # ⬇️ Завантаження музики
        self.weight_data_service = WeightDataService(config=self.config)                 # ⚖️ Дані ваги
        self.delivery_service = MeestDeliveryService(config_service=self.config)         # 🚚 Доставка Meest
        self.formatter = MessageFormatter()                                              # 📝 Форматування текстів
        self.availability_cache = AvailabilityCacheService()                             # 🧊 Кеш доступності
        self.color_size_formatter = ColorSizeFormatter(config_service=self.config)       # 🎨 Перетворення кольорів/розмірів
        self.image_sender = ImageSender(
            exception_handler=self.exception_handler_service,
            constants=self.constants,
        )                                                                                # 🖼️ Відправка зображень з захистом
        logger.debug(
            "🧰 Базові сервіси готові (lang=%s, alt_cache=%s)",
            default_lang,
            alt_cache_max,
        )                                                                                # 🧾 Підсумковий лог

    # ================================
    # 🤖 AI ТА КОНТЕНТ
    # ================================
    def _setup_ai_and_content(self) -> None:
        """
        Готує AI-адаптери, контентні сервіси та генератори.
        """
        self.ai_task_service = AITaskService(
            openai_service=self.openai_service,
            prompts=self.prompt_service,
            cfg=self.config,
        )                                                                                # 🧠 Менеджер AI-завдань
        self.translator_service = self.ai_task_service                                   # 🌐 Перекладач використовує AI Task Service
        self.music_recommendation = MusicRecommendation(
            openai_service=self.openai_service,
            prompt_service=self.prompt_service,
            config_service=self.config,
        )                                                                                # 🎵 Генератор саундтреків
        self.music_sender = MusicSender(
            downloader=self.music_downloader,
            file_manager=self.music_file_manager,
            config=self.config,
        )                                                                                # 📤 Постачальник музики в бот
        self.ocr_service = OCRService(
            openai_service=self.openai_service,
            prompt_service=self.prompt_service,
        )                                                                                # 👁️ OCR через OpenAI
        self.font_service = FontService(config_service=self.config)                      # ✍️ Шрифти для таблиць
        self.table_generator_factory = TableGeneratorFactory(font_service=self.font_service)  # 📊 Побудова таблиць
        raw_gender_rules = self.config.get("hashtags.gender_rules")                      # 🧾 Сирі правила хештегів
        gender_rules = _coerce_gender_rules(raw_gender_rules)                            # 🧼 Нормалізовані правила
        self.gender_classifier = GenderClassifier(gender_rules=gender_rules)             # 🚻 Класифікація тегів
        self.hashtag_generator = HashtagGenerator(
            config_service=self.config,
            openai_service=self.openai_service,
            prompt_service=self.prompt_service,
            gender_rules=gender_rules,
        )                                                                                # 🏷️ Генерація хештегів
        logger.debug("🎨 Контентний стек готовий (rules=%d)", len(gender_rules))         # 🧾 Підсумок контенту

    # ================================
    # 🏭 ДОМЕННІ СЕРВІСИ
    # ================================
    def _setup_domain_services(self) -> None:
        """
        Формує доменні сервіси ціноутворення, ваги та доступності.
        """
        raw_discount = self.config.get("pricing.discount_percentage")                    # 🔻 Відсоток знижки з конфігів
        discount_percent = Decimal("15")                                                 # 🎯 Запасне значення
        if raw_discount is not None:
            try:
                discount_percent = Decimal(str(raw_discount))                             # 🔁 Нормалізуємо у Decimal
            except (InvalidOperation, TypeError, ValueError):                             # ⚠️ Конфіг зіпсований
                logger.warning(
                    "pricing.discount_percentage має невалідне значення %r — використовую 15%%",
                    raw_discount,
                )

        insurance_cfg: Dict[str, Any] = self.config.get("pricing.meest_insurance", {}) or {}
        raw_mode = str(insurance_cfg.get("mode", "none")).strip().lower() or "none"
        if raw_mode not in {"none", "fixed", "percent_cost", "percent_final"}:
            logger.warning(
                "pricing.meest_insurance.mode=%r невідомий — використовую 'none'",
                raw_mode,
            )
            raw_mode = "none"

        def _safe_decimal(value: Any, fallback: str) -> Decimal:
            try:
                return Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                logger.warning(
                    "pricing.meest_insurance значення %r не конвертується у Decimal — використовую %s",
                    value,
                    fallback,
                )
                return Decimal(fallback)

        fixed_usd = _safe_decimal(insurance_cfg.get("fixed_usd", "0"), "0")
        percent = _safe_decimal(insurance_cfg.get("percent", "0"), "0")

        pricing_cfg = PricingConfig(                                            # ⚙️ Формуємо конфіг домену
            discount_percent=discount_percent,
            meest_insurance_mode=raw_mode,
            meest_insurance_fixed_usd=fixed_usd,
            meest_insurance_percent=percent,
        )
        self.pricing_service = PricingService(                                            # 💵 Розрахунок цін
            delivery_service=self.delivery_service,
            cfg=pricing_cfg,
        )
        self.weight_resolver = WeightResolver(
            weight_data_service=cast(Any, self.weight_data_service),
            ai_estimator=cast(Any, self.ai_task_service),
        )                                                                                # ⚖️ Визначення ваги
        self.availability_service = AvailabilityService()                                # 📊 Домен доступності
        logger.debug("🏭 Доменні сервіси готові")                                         # 🧾 Підсумковий лог

    # ================================
    # 🧩 ФАБРИКИ ТА МЕНЕДЖЕРИ
    # ================================
    def _setup_managers(self) -> None:
        """
        Створює фабрики парсерів та менеджери доступності.
        """
        self.parser_factory = ParserFactory(
            webdriver_service=self.webdriver_service,
            translator_service=self.translator_service,
            weight_resolver=self.weight_resolver,
            config_service=self.config,
            url_parser_service=self.url_parser_service,
        )                                                                                # 🧩 Фабрика парсерів
        self.parser_factory_adapter = ParserFactoryAdapter(self.parser_factory)          # 🔌 Адаптер фабрики
        self.availability_report_builder = AvailabilityReportBuilder(
            formatter=self.color_size_formatter
        )                                                                                # 🧱 Побудова звітів доступності
        self.availability_manager = AvailabilityManager(
            availability_service=self.availability_service,
            parser_factory=self.parser_factory,
            cache_service=self.availability_cache,
            report_builder=self.availability_report_builder,
            config_service=self.config,
            url_parser_service=self.url_parser_service,
        )                                                                                # 🗃️ Менеджер доступності
        self.search_resolver: IProductSearchProvider = self.parser_factory.create_search_provider()  # 🔍 Провайдер пошуку
        logger.debug("🧩 ParserFactory та AvailabilityManager готові")                  # 🧾 Загальний стан

    # ================================
    # 🚀 ВИСОКОРІВНЕВІ СЕРВІСИ
    # ================================
    def _setup_high_level_services(self) -> None:
        """
        Будує високорівневі обробники, месенджери та пайплайни обробки.
        """
        self.price_calculator = PriceCalculationHandler(
            currency_manager=self.currency_manager,
            parser_factory=self.parser_factory,
            pricing_service=self.pricing_service,
            config_service=self.config,
            constants=self.constants,
            exception_handler=self.exception_handler_service,
            url_parser_service=self.url_parser_service,
        )                                                                                # 🧮 Розрахунок цін
        self.product_header_service = ProductHeaderService(
            parser_factory=self.parser_factory,
            url_parser_service=self.url_parser_service,
        )                                                                                # 📰 Заголовки товарів
        self.availability_processing_service = AvailabilityProcessingService(
            manager=self.availability_manager,
            header_service=self.product_header_service,
            url_parser_service=self.url_parser_service,
        )                                                                                # 🧮 Процесинг доступності
        self.availability_messenger = AvailabilityMessenger()                            # ✅ Месенджер наявності
        self.availability_handler = AvailabilityHandler(
            processing_service=self.availability_processing_service,
            messenger=self.availability_messenger,
        )                                                                                # 📬 Відповіді щодо наявності
        self.content_service = ProductContentService(
            translator=self.translator_service,
            hashtag_generator=self.hashtag_generator,
            price_handler=self.price_calculator,
            alt_text_generator=self.alt_text_generator,
        )                                                                                # 📝 Збагачення контенту
        self.image_downloader = ImageDownloader(compute_sha256=True)                     # 🖼️ Завантаження з SHA кешем
        self.product_media_preparer = ProductMediaPreparer(                               # 🧰 Підготовка стеку фото
            downloader=ImageDownloader(max_attempts=3, backoff_base_s=0.8),
        )
        self.size_chart_finder = YoungLASizeChartFinder()                                # 🧭 Пошук таблиць YoungLA
        self.product_gender_detector = YoungLAProductGenderDetector()                    # 🚻 Детектор статі товару
        self.size_chart_service = SizeChartService(
            downloader=self.image_downloader,
            ocr_service=self.ocr_service,
            generator_factory=self.table_generator_factory,
            size_chart_finder=self.size_chart_finder,
            product_gender_detector=self.product_gender_detector,
        )                                                                                # 📏 Побудова таблиць розмірів
        self.processing_service = ProductProcessingService(
            parser_factory=self.parser_factory,
            availability_processing_service=self.availability_processing_service,
            content_service=self.content_service,
            music_recommendation=self.music_recommendation,
            url_parser_service=self.url_parser_service,
            size_chart_service=self.size_chart_service,
        )                                                                                # ⚙️ Комплексна обробка товару
        self.size_chart_messenger = SizeChartMessenger(
            image_sender=self.image_sender,
            exception_handler=self.exception_handler_service,
        )                                                                                # 📐 Відправка таблиць розмірів
        self.size_chart_handler = SizeChartHandlerBot(
            parser_factory=self.parser_factory,
            size_chart_service=self.size_chart_service,
            messenger=self.size_chart_messenger,
            exception_handler=self.exception_handler_service,
            constants=self.constants,
        )                                                                                # 📏 Хендлер таблиць
        self.messenger = ProductMessenger(
            music_sender=self.music_sender,
            size_chart_handler=self.size_chart_handler,
            formatter=self.formatter,
            image_sender=self.image_sender,
            exception_handler=self.exception_handler_service,
            constants=self.constants,
        )                                                                                # 📨 Месенджер товарів
        self.product_handler = ProductHandler(
            currency_manager=self.currency_manager,
            processing_service=self.processing_service,
            messenger=self.messenger,
            media_preparer=self.product_media_preparer,
            exception_handler=self.exception_handler_service,
            constants=self.constants,
            url_parser_service=self.url_parser_service,
        )                                                                                # 🛒 Основний продукт-хендлер
        self.collection_processing_service = CollectionProcessingService(
            parser_factory=self.parser_factory_adapter,
            url_parser=self.url_parser_service,
        )                                                                                # 🧺 Обробка колекцій
        collection_max_items = _optional_int(self.config.get("collection.max_items", 50, cast=int), 50)  # 🔢 Обмеження елементів
        collection_concurrency = _int_or_default(self.config.get("collection.concurrency", 4, cast=int), 4)  # 🚦 Паралельність
        collection_retries = _int_or_default(self.config.get("collection.per_item_retries", 2, cast=int), 2)  # ♻️ Повтори
        self.collection_handler = CollectionHandler(
            product_handler=self.product_handler,
            url_parser_service=self.url_parser_service,
            collection_processing_service=self.collection_processing_service,
            exception_handler=self.exception_handler_service,
            constants=self.constants,
            max_items=collection_max_items,
            concurrency=collection_concurrency,
            per_item_retries=collection_retries,
        )                                                                                # 🧺 Хендлер колекцій
        logger.debug(
            "🚀 High-level сервіси готові (collections max=%s, concurrency=%s)",
            collection_max_items,
            collection_concurrency,
        )                                                                                # 🧾 Стан високорівневих сервісів
        banner_cfg = self.config.get("banner_drop", {}) or {}
        banner_max_titles = _int_or_default(banner_cfg.get("max_product_titles"), 9)
        banner_cache = _int_or_default(banner_cfg.get("processed_cache_size"), 5)
        self.banner_drop_service = BannerDropService(
            webdriver_service=self.webdriver_service,
            url_parser_service=self.url_parser_service,
            collection_processing_service=self.collection_processing_service,
            product_processing_service=self.processing_service,
            ai_service=self.ai_task_service,
            image_downloader=self.image_downloader,
            image_sender=self.image_sender,
            collection_handler=self.collection_handler,
            constants=self.constants,
            exception_handler=self.exception_handler_service,
            max_product_titles=banner_max_titles,
            processed_cache_size=banner_cache,
        )                                                                                # 🪧 Banner drop сценарій

    # ================================
    # 📚 ФІЧІ ТА РОУТЕРИ
    # ================================
    def _setup_features_and_handlers(self) -> None:
        """
        Реєструє Telegram-фічі, callback-и та роутери посилань.
        """
        self.callback_registry = CallbackRegistry()                                      # 📚 Реєстр callback-ів
        self.features = [
            CoreCommandsFeature(registry=self.callback_registry, constants=self.constants),  # 🧱 Базові команди
            CurrencyFeature(
                currency_manager=self.currency_manager,
                registry=self.callback_registry,
                constants=self.constants,
                exception_handler=self.exception_handler_service,
            ),                                                                           # 💱 Курсові фічі
        ]                                                                                # 📦 Список фіч
        self.callback_handler = CallbackHandler(
            registry=self.callback_registry,
            exception_handler=self.exception_handler_service,
        )                                                                                # 🔄 Центральний callback-хендлер
        self.link_handler = LinkHandler(
            product_handler=self.product_handler,
            collection_handler=self.collection_handler,
            size_chart_handler=self.size_chart_handler,
            price_calculator=self.price_calculator,
            availability_handler=self.availability_handler,
            banner_drop_service=self.banner_drop_service,
            search_resolver=self.search_resolver,
            url_parser_service=self.url_parser_service,
            currency_manager=self.currency_manager,
            constants=self.constants,
            exception_handler=self.exception_handler_service,
        )                                                                                # 🔗 Роутер вхідних посилань
        self.order_file_handler = OrderFileHandler(
            order_service=self.youngla_order_service,
            exception_handler=self.exception_handler_service,
        )                                                                                # 📂 Обробник .txt-замовлень
        self.main_menu_feature = MainMenuFeature(constants=self.constants)               # 📋 Фіча головного меню
        self.menu_handler = self.main_menu_feature                                      # ♻️ Зворотна сумісність сеансу
        logger.debug("📚 Фічі та роутери ініціалізовані (%d)", len(self.features))       # 🧾 Стан реєстрації
