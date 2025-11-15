# 🏭 app/infrastructure/parsers/parser_factory.py
"""
🏭 ParserFactory — фабрика, що будує парсери товарів, колекцій та пошуку.

🔹 Інкапсулює загальні залежності (webdriver, перекладач, конфіги, ваги).
🔹 Вирівнює параметри (HTML-парсер, локаль, таймаути) та пише діагностику.
🔹 Повертає строго типізовані інстанси `BaseParser`, `UniversalCollectionParser`, `ProductSearchResolver`.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging	# 🧾 Логування активності фабрики
from typing import Any, Final, Optional, final									# 🧰 Типи та final-декоратор

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService	# ⚙️ Доступ до конфіга
from app.domain.products.services.weight_resolver import WeightResolver	# ⚖️ Обрахунок ваги
from app.infrastructure.ai.ai_task_service import AITaskService as TranslatorService	# 🌐 Переклад/AI
from app.infrastructure.web.webdriver_service import WebDriverService	# 🕸️ Завантаження сторінок
from app.shared.utils.locale import normalize_locale	# 🗺️ Єдина нормалізація локалі
from app.shared.utils.logger import LOG_NAME	# 🏷️ Базове імʼя логера
from app.shared.utils.url_parser_service import UrlParserService	# 🔗 Допоміжні дії з URL

from ._infra_options import ParserInfraOptions as _InfraOptions	# 🧱 Інфра-опції за замовчуванням
from .base_parser import BaseParser	# 🧱 Парсер товару
from .collections.universal_collection_parser import UniversalCollectionParser	# 📚 Парсер колекцій
from .product_search.search_resolver import ProductSearchResolver	# 🔍 Провайдер пошуку

# ================================
# 🧾 ЕКСПОРТ МОДУЛЯ
# ================================
__all__: Final = ["ParserFactory", "ParserInfraOptions"]	# 📦 Публічні символи
ParserInfraOptions = _InfraOptions	# 🔁 Re-export alias для зовнішнього імпорту

# ================================
# ⚙️ КОНСТАНТИ ТА ЛОГЕР
# ================================
_ALLOWED_HTML_PARSERS: tuple[str, ...] = ("lxml", "html.parser", "html5lib")	# ⚙️ Дозволені HTML-парсери
logger = logging.getLogger(f"{LOG_NAME}.parser.factory")	# 🧾 Іменований логер фабрики


@final
class ParserFactory:
    """
    🏭 Інкапсулює побудову всіх типів парсерів із єдиними опціями.
    """

    __slots__ = (
        "_webdriver_service",	# 🌐 Playwright/driver клієнт
        "_translator_service",	# 🌎 AI перекладач
        "_weight_resolver",	# ⚖️ Розрахунок ваги товару
        "_config_service",	# ⚙️ Джерело конфігів
        "_url_parser_service",	# 🔗 Нормалізація посилань
        "_default_options",	# 🧾 Інфра-опції за замовчуванням
        "_log",	# 🧾 Інстансний логер
    )

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        webdriver_service: WebDriverService,
        translator_service: TranslatorService,
        weight_resolver: WeightResolver,
        config_service: ConfigService,
        url_parser_service: UrlParserService,
        default_options: _InfraOptions | None = None,
    ) -> None:
        """
        ⚙️ Зберігає залежності та готує дефолтні опції.
        """
        self._webdriver_service = webdriver_service	# 🌐 Завантаження HTML
        self._translator_service = translator_service	# 🌎 AI/переклад
        self._weight_resolver = weight_resolver	# ⚖️ Обробка ваги товару
        self._config_service = config_service	# ⚙️ Конфігураційний сервіс
        self._url_parser_service = url_parser_service	# 🔗 Нормалізація URL
        self._default_options = default_options or _InfraOptions.default()	# 🧾 Інфра-опції з fallback
        self._log = logging.getLogger(f"{logger.name}.instance")				# 🧾 Локальний логер фабрики
        self._log.debug(
            "🏗️ ParserFactory ініціалізовано (webdriver=%s translator=%s options=%s).",
            type(webdriver_service).__name__,
            type(translator_service).__name__,
            self._default_options,
        )

        try:
            level = self._default_options.effective_log_level()	# 🎚️ Рівень логів із опцій
            logging.getLogger(LOG_NAME).setLevel(level)	# 🧾 Синхронізуємо кореневий логер підсистеми
            self._log.setLevel(level)	# 🧾 Вирівнюємо інстансний логер
            self._log.debug("🧭 ParserFactory ініціалізовано (log_level=%s).", level)	# 🪵 Фіксуємо ініціалізацію
        except Exception as exc:	# ⚠️ Непередбачений збій читання опцій
            self._log.warning("⚠️ Не вдалося застосувати log level з опцій: %s", exc)	# ⚠️ Фіксуємо проблему

    # ================================
    # 🧰 СЛУЖБОВІ МЕТОДИ
    # ================================
    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        🧼 Прибирає зайві пробіли й розширює протоколи у відносних URL.
        """
        raw_url = (url or "").strip()	# ✂️ Очищаємо вхід
        if not raw_url:	# 🚫 Порожня строка після обрізки
            logger.debug("🔗 normalize_url: отримано порожнє значення.")	# 🪵 Діагностика пустого вводу
            return raw_url	# ⛔️ Повертаємо як є
        if raw_url.startswith("//"):	# 🌐 Протокол-agnostic URL
            normalized = f"https:{raw_url}"	# 🔗 Додаємо https-префікс
            logger.debug("🔗 normalize_url: префіксовано https (%s).", normalized)	# 🪵 Фіксуємо зміну
            return normalized	# ✅ Повертаємо нормалізований URL
        if raw_url.startswith(("http://", "https://")):	# 🌐 Уже абсолютний URL
            return raw_url	# 🔁 Повертаємо без змін
        logger.debug("🔗 normalize_url: повернуто вихідний URL без протоколу (%s).", raw_url)	# 🪵 Інфо про незмінений URL
        return raw_url	# 🔁 Строка без змін

    def _pick_html_parser(self, name: Optional[str]) -> str:
        """
        🧮 Перевіряє, чи запитаний HTML-парсер у білому списку.
        """
        if name in _ALLOWED_HTML_PARSERS:	# ✅ Дозволений варіант
            logger.debug("🧮 HTML parser '%s' дозволений, використовуємо його.", name)	# 🪵 Фіксуємо вибір
            return name	# 🔁 Повертаємо валідне значення
        if name is not None:	# ⚠️ Передано заборонений парсер
            logger.warning("⚠️ Невідомий HTML parser '%s' → fallback на 'lxml'.", name)	# ⚠️ Жовтий прапорець
        return "lxml"	# 🔁 Повертаємо дефолт

    @staticmethod
    def _ensure_non_empty_url(url: str, who: str) -> None:
        """
        🛡️ Гарантує, що URL непорожній перед побудовою парсера.
        """
        if not isinstance(url, str) or not url.strip():	# 🚫 Невалідний вхід
            logger.error("❌ %s: отримано порожній URL.", who)	# 🧨 Логуємо помилку
            raise ValueError(f"{who}: 'url' must be a non-empty string")	# 🛑 Зупиняємо виконання

    # ================================
    # 🧾 ПУБЛІЧНИЙ API
    # ================================
    def create_product_parser(self, url: str, **overrides: Any) -> BaseParser:
        """
        🧾 Створює `BaseParser` із урахуванням override-параметрів.
        """
        self._ensure_non_empty_url(url, "ParserFactory.create_product_parser")	# 🛡️ Перевіряємо URL
        norm_url = self._normalize_url(url)	# 🧼 Приводимо URL до абсолюту

        opts = self._default_options	# 🧾 Дефолтні опції для fallback
        html_parser = self._pick_html_parser(overrides.get("html_parser", opts.html_parser))	# 🧮 Вибір HTML-парсера
        enable_progress = bool(overrides.get("enable_progress", opts.enable_progress))	# ⏳ Контроль прогресбару
        request_timeout_sec = float(overrides.get("request_timeout_sec", opts.request_timeout_sec))	# ⏱️ Таймаути запиту
        images_limit = int(overrides.get("images_limit", opts.images_limit))	# 🖼️ Ліміт зображень
        user_agent = overrides.get("user_agent", opts.user_agent)	# 🕵️‍♂️ Користувацький агент

        cfg_default = self._config_service.get("default_language", "uk", str) or "uk"	# 🗺️ Fallback локалі з YAML
        raw_locale = overrides.get("locale", opts.locale) or cfg_default	# 🗺️ Вихідна локаль
        locale = normalize_locale(raw_locale, default=cfg_default)	# 🧭 Нормалізуємо локаль

        kwargs: dict[str, Any] = {
            "url": norm_url,	# 🔗 Абсолютний URL
            "webdriver_service": self._webdriver_service,	# 🌐 Веб-драйвер
            "translator_service": self._translator_service,	# 🌎 Перекладач
            "config_service": self._config_service,	# ⚙️ Конфіги
            "weight_resolver": self._weight_resolver,	# ⚖️ Розрахунок ваги
            "url_parser_service": self._url_parser_service,	# 🔗 Допоміжний сервіс URL
            "html_parser": html_parser,	# 🧮 Обраний HTML-парсер
            "enable_progress": enable_progress,	# ⏳ Показувати прогрес
            "request_timeout_sec": int(request_timeout_sec),	# ⏱️ Таймаут (int)
            "images_limit": images_limit,	# 🖼️ Ліміт зображень
            "locale": locale,	# 🗺️ Робоча локаль
            "user_agent": user_agent,	# 🕵️‍♂️ Користувацький агент
        }
        self._log.info(
            "🧾 Створюємо product parser (url=%s, locale=%s, parser=%s, timeout=%s).",
            norm_url,
            locale,
            html_parser,
            request_timeout_sec,
        )	# 🪵 Логуємо ключові параметри
        parser = BaseParser(**kwargs)	# 🏗️ Будуємо екземпляр парсера
        self._log.debug("🧾 Product parser готовий: %s.", parser)
        return parser

    def create_collection_parser(self, url: str) -> UniversalCollectionParser:
        """
        📚 Створює парсер колекцій із дефолтними інфра-опціями.
        """
        self._ensure_non_empty_url(url, "ParserFactory.create_collection_parser")	# 🛡️ Перевіряємо URL
        norm_url = self._normalize_url(url)	# 🔗 Нормалізуємо адресу
        html_parser = self._pick_html_parser(self._default_options.html_parser)	# 🧮 Фіксуємо HTML-парсер
        self._log.info("📚 Створюємо collection parser (url=%s, parser=%s).", norm_url, html_parser)	# 🪵 Діагностика
        return UniversalCollectionParser(
            url=norm_url,	# 🔗 Нормалізований URL
            webdriver_service=self._webdriver_service,	# 🌐 Драйвер
            config_service=self._config_service,	# ⚙️ Конфіги
            url_parser_service=self._url_parser_service,	# 🔗 URL-утиліти
            html_parser=html_parser,	# 🧮 Парсер DOM
        )	# 🏗️ Повертаємо екземпляр

    def create_search_provider(self) -> ProductSearchResolver:
        """
        🔍 Повертає строго типізований провайдер пошуку товарів.
        """
        self._log.info("🔍 Створюємо search provider (locale=%s).", self._default_options.locale)	# 🪵 Фіксуємо подію
        provider = ProductSearchResolver(
            webdriver_service=self._webdriver_service,	# 🌐 Драйвер
            url_parser_service=self._url_parser_service,	# 🔗 Утиліти URL
            config_service=self._config_service,	# ⚙️ Конфіги
            infra_options=self._default_options,	# 🧾 Інфра-опції
        )	# 🏗️ Повертаємо провайдер
        self._log.debug("🔍 Провайдер пошуку створено: %s.", provider)
        return provider
