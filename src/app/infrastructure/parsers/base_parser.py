# 🧠 src/app/infrastructure/parsers/base_parser.py
"""
🧠 BaseParser — оркестратор повного циклу парсингу сторінки товару.

🔹 Завантажує HTML (із LRU-кешем), витягує сирі дані та формує `ProductInfo`.
🔹 Нормалізує ціну, зображення, секції, дані про наявність і вагу.
🔹 Підтримує fallback для опису, обмеження зображень і кастомний User-Agent.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup										# 🥣 HTML-парсер
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn	# ⏳ Індикація завантаження

# 🔠 Системні імпорти
import logging														# 🧾 Логування подій
from decimal import Decimal										# 💰 Робота з фінансовими значеннями
from typing import Any, Dict, Optional, Union, cast				# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService				# ⚙️ Конфігураційний сервіс
from app.domain.products.dto import ProductHeaderDTO				# 📦 DTO заголовка
from app.domain.products.entities import Currency, ProductInfo, Url	# 🧾 Доменні сутності
from app.domain.products.interfaces import IProductDataProvider	# 🤝 Контракт провайдера даних
from app.domain.products.services.weight_resolver import WeightResolver	# ⚖️ Визначення ваги
from app.infrastructure.ai.ai_task_service import AITaskService as TranslatorService	# 🌐 Переклади/AI
from app.infrastructure.web.webdriver_service import WebDriverService	# 🌍 Завантаження через Playwright
from app.shared.cache.html_lru_cache import HtmlLruCache			# 🧠 LRU-кеш HTML (IMP-034)
from app.shared.errors import NetworkError, OcrError, ParseError	# 🚨 Резервні винятки для розширень  # noqa: F401
from app.shared.utils.collections import uniq_keep_order			# ♻️ Дедуплікація зі збереженням порядку
from app.shared.utils.immutables import freeze					# 🧊 Іммʼютабельні структури
from app.shared.utils.logger import LOG_NAME						# 🏷️ Базове імʼя логера
from app.shared.utils.number import decimal_from_price_str			# 💵 Нормалізація цін
from app.shared.utils.size_norm import normalize_stock_map			# 📏 Нормалізація розмірів
from app.shared.utils.url_parser_service import UrlParserService	# 🌍 Витяг валюти/даних із URL

from .html_data_extractor import HtmlDataExtractor					# 🧾 Витяг даних із DOM


# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
logger = logging.getLogger(LOG_NAME)                                # 🧾 Логер модуля


# ================================
# 🏛️ ПАРСЕР
# ================================
class BaseParser(IProductDataProvider):
    """
    🏛️ Повний цикл обробки товару: HTML → сирі дані → обробка → `ProductInfo`.

    Налаштовувані поведінки:
      • `enable_description_fallback`: підміняє опис першою секцією, якщо короткий.
      • `description_fallback_min_len`: поріг довжини опису.
      • `images_limit`, `filter_small_images`: тюнінг списку зображень.
      • Підтримує кастомний `User-Agent` та HTML-кеш (IMP-034).
    """

    HTML_PARSER: str = "lxml"                                         # 🧰 Дефолтний парсер BeautifulSoup

    def __init__(
        self,
        url: Union[str, Url],
        webdriver_service: WebDriverService,
        translator_service: TranslatorService,
        config_service: ConfigService,
        weight_resolver: WeightResolver,
        url_parser_service: UrlParserService,
        *,
        enable_progress: bool = True,
        html_parser: Optional[str] = None,
        request_timeout_sec: int = 30,
        enable_description_fallback: Optional[bool] = None,
        description_fallback_min_len: Optional[int] = None,
        images_limit: Optional[int] = None,
        filter_small_images: Optional[bool] = None,
        locale: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.url: Url = url if isinstance(url, Url) else Url(url)       # 🌍 Стандартизуємо URL
        self.webdriver_service = webdriver_service                       # 🌐 Playwright клієнт
        self.translator_service = translator_service                     # 🌎 Адаптер AI/перекладів
        self.config_service = config_service                             # ⚙️ Конфігураційний сервіс
        self.weight_resolver = weight_resolver                           # ⚖️ Сервіс визначення ваги
        self.url_parser_service = url_parser_service                     # 🌍 Допоміжний сервіс URL

        self.enable_progress = bool(enable_progress)                     # ⏳ Чи показувати прогрес

        allowed_parsers = {"lxml", "html.parser", "html5lib"}			# ✅ Безпечний список парсерів
        chosen_parser = html_parser or self.HTML_PARSER					# 🧰 Перевага кастомного парсера
        if chosen_parser not in allowed_parsers:						# 🚫 Перевіряємо чи парсер дозволений
            logger.warning("⚠️ Невідомий HTML-парсер '%s' → використовуємо '%s'", chosen_parser, self.HTML_PARSER)	# 🛎️ Попереджаємо про fallback
        self.html_parser = chosen_parser if chosen_parser in allowed_parsers else self.HTML_PARSER	# 🥣 Фактичний HTML-парсер

        try:															# 🛡️ Нормалізуємо таймаут запиту
            self.request_timeout_sec = max(1, int(request_timeout_sec))	# ⏱️ Мінімум 1 сек
        except Exception:	# noqa: BLE001								# ⚠️ Некоректне значення таймауту
            self.request_timeout_sec = 30								# ⏱️ Повертаємося до дефолтного таймауту

        currency_str: Optional[str]										# 💱 Буфер для валюти з URL
        try:															# 🛡️ Пробуємо дістати валюту з URL
            currency_candidate = self.url_parser_service.get_currency(self.url.value, default=None)	# 🔍 Зчитуємо валюту з URL
            currency_str = currency_candidate.upper() if currency_candidate else None	# 🔤 Нормалізуємо валюту
        except Exception:	# noqa: BLE001								# ⚠️ Не вдалося прочитати валюту
            currency_str = None											# 🚫 Немає валюти в URL
        self._currency_str = currency_str                                # 💱 Кеш валюти

        self.page_source: Optional[str] = None                           # 🧾 HTML-код сторінки
        self._page_soup: Optional[BeautifulSoup] = None                  # 🥣 Розпарсений DOM

        fallback_enabled: bool											# ✅ Прапор fallback опису
        fallback_min_len: int											# 🔢 Мінімальна довжина опису
        try:															# 🛡️ Зчитуємо налаштування fallback із конфігурації
            cfg_enabled = bool(self.config_service.get("parser.description_fallback.enabled", True))	# ⚙️ Читаємо прапор із конфігурації
            cfg_min_len_raw = self.config_service.get("parser.description_fallback.min_len", 20, cast=int)	# ⚙️ Порогова довжина
            fallback_min_len = int(cfg_min_len_raw if cfg_min_len_raw is not None else 20)	# 🔢 Нормалізуємо значення
            fallback_enabled = cfg_enabled								# ✅ Пам'ятаємо глобальне налаштування
        except Exception:	# noqa: BLE001	# ⚠️ Некоректні налаштування fallback
            fallback_enabled, fallback_min_len = True, 20				# 🛟 Використовуємо безпечні дефолти

        self.enable_description_fallback = bool(
            fallback_enabled if enable_description_fallback is None else enable_description_fallback
        )                                                                # 🧾 Прапор fallback
        fallback_min_len_value = (
            description_fallback_min_len if description_fallback_min_len is not None else fallback_min_len
        )                                                                # 📏 Пріоритезуємо аргумент конструктора
        try:															# 🛡️ Валідуємо поріг fallback-опису
            self.description_fallback_min_len = int(fallback_min_len_value)	# 📏 Мінімальна довжина опису
        except Exception:	# noqa: BLE001	# ⚠️ Не вдалося привести довжину до int
            self.description_fallback_min_len = 20						# 🛟 Фолбек довжини опису

        try:															# 🛡️ Обробляємо ліміт зображень
            limit_raw = images_limit if images_limit is not None else 30	# 🧮 Базове значення ліміту зображень
            limit_value = int(limit_raw)									# 🔢 Нормалізуємо до int
            if limit_value < 1:											# 🚫 Мінімальне обмеження
                limit_value = 1											# 🔧 Виправляємо нижню межу
            elif limit_value > 200:										# 🚫 Гарантуємо відсутність надмірного кешу
                limit_value = 200										# 🔧 Встановлюємо верхню межу
            self.images_limit = limit_value								# 🖼️ Ліміт зображень
        except Exception:	# noqa: BLE001	# ⚠️ Некоректний ліміт зображень
            self.images_limit = 30										# 🛟 Стандартний ліміт зображень

        try:															# 🛡️ Обробляємо прапор фільтрації зображень
            filter_flag = filter_small_images if filter_small_images is not None else True	# 🔍 Визначаємо чи фільтруємо
            self.filter_small_images = bool(filter_flag)					# 🔍 Прапор фільтра малих зображень
        except Exception:	# noqa: BLE001	# ⚠️ Некоректне значення фільтрації
            self.filter_small_images = True								# 🛟 Завжди вмикаємо фільтр за змовчанням

        self.locale = locale or "uk"									# 🌐 Локаль для екстрактора
        self.user_agent = user_agent or None								# 🕵️ Кастомний User-Agent
        self._log = logging.getLogger(f"{logger.name}.base_parser")		# 🧾 Інстансний логер парсера

        self._html_cache = HtmlLruCache(									# 🧠 HTML LRU-кеш (IMP-034)
            max_entries=self._cfg_int("parser.html_cache.max_entries", 256),	# 🧮 Місткість кешу
            ttl_sec=self._cfg_int("parser.html_cache.ttl_sec", 300),		# ⏳ Час життя кешу
        )
        self._html_cache_enabled = bool(self.config_service.get("parser.html_cache.enabled", True))	# 🧠 Чи ввімкнений кеш
        key_strategy_raw = self.config_service.get("parser.html_cache.key_strategy", "url", cast=str) or "url"	# 🔑 Стратегія ключа кешу
        self._html_cache_key_strategy = key_strategy_raw.lower()			# 🔑 Нормалізований ідентифікатор стратегії
        self._log.debug(
            "🧠 BaseParser init: cache=%s strategy=%s locale=%s html_parser=%s timeout=%s images_limit=%s filter_small=%s",
            self._html_cache_enabled,
            self._html_cache_key_strategy,
            self.locale,
            self.html_parser,
            self.request_timeout_sec,
            self.images_limit,
            self.filter_small_images,
        )																		# 🧾 Контекст конфігурації

    # ================================
    # 🔄 ПУБЛІЧНИЙ API
    # ================================
    async def get_product_info(self) -> ProductInfo:
        """
        🔄 Основний метод: повертає валідований `ProductInfo`.

        Returns:
            ProductInfo: Іммʼютабельна доменна сутність товару.
        """
        try:
            await self._fetch_and_prepare_soup()                        # 🌍 Завантажуємо HTML-код
            if not self._page_soup:                                     # 🚫 DOM відсутній після завантаження
                raise ConnectionError("Не вдалося завантажити або розпарсити HTML.")  # 🛑 Допоміжне повідомлення

            extractor = self._make_extractor(self._page_soup, self.locale)  # 🧾 Створюємо екстрактор
            raw_data = self._extract_raw_data(extractor)                # 🛈 Витягуємо сирі дані
            processed = await self._process_data(raw_data)              # ✨ Збагачуємо дані
            info = self._build_product_info(processed)                  # 🏗️ Формуємо ProductInfo
            return self._validate_info(info)                            # ✅ Перевіряємо фінальний результат

        except Exception as exc:  # noqa: BLE001  # ⚠️ Непередбачена помилка під час парсингу
            logger.exception("❌ Помилка під час парсингу %s: %s", self.url.value, exc)  # 🧨 Логуємо збій
            return ProductInfo(										# 🛟 Створюємо fallback ProductInfo
                title=_fallback_title_from_url(self.url),              # 🏷️ Безпечний заголовок
                price=Decimal("0.0"),                                  # 💵 Нульова ціна для помилки
                description="Не вдалося отримати дані",               # 🧾 Повідомлення користувачу
                currency=_safe_currency(self._currency_str),           # 💱 Повертаємо дефолтну валюту
            )                                                          # 🛟 Повертаємо безпечний об'єкт

    async def get_header_info(self) -> ProductHeaderDTO:
        """
        🧾 Легковаговий виклик: заголовок та головне зображення для превʼю.

        Returns:
            ProductHeaderDTO: DTO із заголовком, зображенням і URL.
        """
        if self._page_soup is None:                                     # 🔄 DOM ще не готовий
            await self._fetch_and_prepare_soup()                        # 🌍 Підтягуємо HTML і парсимо

        title = "ТОВАР"                                                 # 🏷️ Базовий заголовок
        image_url: Optional[str] = None                                 # 🖼️ Плейсхолдер для зображення

        if self._page_soup is not None:                                 # ✅ Працюємо з готовим DOM
            extractor = self._make_extractor(self._page_soup, self.locale)  # 🧾 Створюємо екстрактор
            extracted_title = extractor.extract_title()                  # 🏷️ Читаємо заголовок зі сторінки
            if extracted_title:                                         # ✅ Переконуємося, що заголовок не порожній
                title = extracted_title                                 # 🏷️ Оновлюємо заголовок
            extracted_image = extractor.extract_main_image()            # 🖼️ Підтягуємо головне зображення
            if extracted_image:                                         # ✅ Переконуємося в наявності URL
                image_url = extracted_image                             # 🖼️ Запам'ятовуємо зображення

        return ProductHeaderDTO(title=title, image_url=image_url, product_url=self.url)  # 📦 Повертаємо DTO заголовка

    # ================================
    # 🌐 ЗАВАНТАЖЕННЯ HTML
    # ================================
    async def _fetch_and_prepare_soup(self) -> None:
        """
        🌐 Завантажує HTML, використовуючи LRU-кеш (якщо увімкнено), та створює `BeautifulSoup`.
        """
        url_str = self.url.value                                        # 🌍 Поточний URL товару
        cache_key = self._make_cache_key(url_str)                       # 🔑 Генеруємо ключ кешу

        if self._html_cache_enabled:                                    # 🧠 Перевіряємо, чи доступний кеш
            cached_html = await self._html_cache.get(cache_key)         # 📦 Пробуємо взяти вміст із кешу
            if cached_html:                                             # ✅ Знайдено HTML у кеші
                self.page_source = cached_html                          # 🧾 Використовуємо кешований HTML
                self._page_soup = BeautifulSoup(self.page_source, self.html_parser)  # 🥣 Відновлюємо DOM
                logger.info("🟢 HTML із кешу (%d байт): %s", len(self.page_source), url_str)  # 🧾 Логуємо успіх
                return                                                  # ↩️ Далі обробка не потрібна

        key_lock = (
            await self._html_cache.key_lock(cache_key) if self._html_cache_enabled else None
        )                                                                # 🔐 Лок для уникнення гонок

        if key_lock:                                                     # 🔐 Працюємо під lock-ом
            async with key_lock:                                         # 🔐 Синхронізуємо конкурентні запити
                cached_html = await self._html_cache.get(cache_key)     # 📦 Перевіряємо кеш повторно
                if cached_html:                                         # ✅ Кеш міг зʼявитися поки чекали
                    self.page_source = cached_html                      # 🧾 Використовуємо кеш
                    self._page_soup = BeautifulSoup(self.page_source, self.html_parser)  # 🥣 Відновлюємо DOM
                    logger.info("🟢 HTML із кешу після lock (%d байт): %s", len(self.page_source), url_str)  # 🧾 Лог успіху
                    return                                              # ↩️ Завершуємо
                await self._load_html_and_build_soup(url_str)           # 🌍 Завантажуємо HTML з мережі
                if self.page_source and self._html_cache_enabled:       # 🧠 Зберігаємо результат у кеші
                    await self._html_cache.set(cache_key, self.page_source)  # 💾 Кешуємо HTML
                return                                                  # ↩️ Завершуємо після обробки

        await self._load_html_and_build_soup(url_str)                    # 🌍 Пряме завантаження без lock-у

    async def _load_html_and_build_soup(self, url_str: str) -> None:
        """
        ⬇️ Завантажує HTML через `WebDriverService` та формує `BeautifulSoup`.
        """
        logger.info("🌍 Завантаження %s … (timeout=%ss)", url_str, self.request_timeout_sec)  # 🧾 Фіксуємо початок
        task_description = f"Завантаження [cyan]{url_str.split('/')[-1]}[/cyan]…"  # 📝 Підпис для прогрес-бару

        goto_kwargs: Dict[str, Any] = {								# ⚙️ Параметри переходу для Playwright
            "wait_until": "networkidle",                                # 🕸️ Чекаємо поки мережа стихне
            "timeout_ms": self.request_timeout_sec * 1000,              # ⏱️ Перетворюємо секунди у мс
        }                                                               # ⚙️ Параметри Playwright
        if self.user_agent:                                             # 🕵️ Чи потрібно підмінити User-Agent
            goto_kwargs["user_agent"] = self.user_agent                 # 🕵️ Підставляємо кастомний заголовок

        if self.enable_progress:                                        # ⏳ Відображаємо індикатор прогресу
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                transient=True,
            ) as progress:                                              # ⏳ Запускаємо прогрес-бар
                progress.add_task(description=task_description, total=None)  # 📊 Додаємо задачу
                self.page_source = await self.webdriver_service.get_page_content(url_str, **goto_kwargs)  # 🌐 Отримуємо HTML
        else:
            self.page_source = await self.webdriver_service.get_page_content(url_str, **goto_kwargs)  # 🌐 Отримуємо HTML без прогресу

        if self.page_source:                                            # ✅ Контент отримано
            self._page_soup = BeautifulSoup(self.page_source, self.html_parser)  # 🥣 Створюємо DOM
            logger.info("✅ Завантажено (%d байт).", len(self.page_source))  # 🧾 Логуємо успіх
        else:
            logger.error("❌ Неможливо завантажити HTML: %s", url_str)   # ❌ Повідомляємо про невдачу

    # ================================
    # 📥 ВИТЯГ СИРИХ ДАНИХ
    # ================================
    def _extract_raw_data(self, extractor: HtmlDataExtractor) -> Dict[str, Any]:
        """
        📥 Структурує сирі дані, отримані від екстрактора.
        """
        self._log.debug("📥 Починаємо екстракцію сирих даних.")
        images = extractor.extract_all_images(
            limit=self.images_limit,
            filter_small_images=self.filter_small_images,
        )                                                               # 🖼️ Вибірка усіх релевантних зображень
        raw_data = {														# 🧾 Формуємо структуру сирих даних
            "title": extractor.extract_title(),                         # 🏷️ Сирий заголовок
            "price": extractor.extract_price(),                         # 💵 Сире значення ціни
            "description": extractor.extract_description(),             # 📝 Основний опис
            "main_image": extractor.extract_main_image(),               # 🖼️ Головне зображення
            "all_images": images,                                       # 🖼️ Усі релевантні зображення
            "sections": extractor.extract_detailed_sections(),          # 📚 Детальні секції
            "stock_data": self._get_stock_with_fallback(extractor),     # 📦 Дані про наявність
        }                                                               # 🧾 Сирий словник даних
        self._log.debug(
            "📥 Сирі дані: title='%s', price=%s, images=%d, sections=%d.",
            raw_data["title"],
            raw_data["price"],
            len(raw_data["all_images"] or []),
            len(raw_data["sections"] or {}),
        )                                                               # 🪵 Статистика
        return raw_data

    # ================================
    # ✨ ОБРОБКА ДАНИХ
    # ================================
    async def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✨ Додає похідні дані (fallback опису, вага тощо).
        """
        if self.enable_description_fallback:							# 🧾 Увімкнено fallback опису
            description = str(data.get("description") or "").strip()	# 📝 Обрізаємо опис
            if len(description) < int(self.description_fallback_min_len or 0):	# 🪫 Перевіряємо довжину опису
                sections = data.get("sections") or {}					# 📚 Беремо секції опису
                first_key = next(iter(sections), None)					# 🔑 Дістаємо перший ключ секції
                if first_key:											# ✅ Є хоча б одна секція
                    data["description"] = sections[first_key]			# 🔄 Підміняємо опис першою секцією

        title = str(data.get("title") or "").strip()					# 🏷️ Нормалізуємо заголовок
        description = str(data.get("description") or "")				# 📝 Актуальний опис
        image_url = str(data.get("main_image") or "")					# 🖼️ Посилання на головне фото

        try:															# 🛡️ Рахуємо вагу через сервіс
            resolved_weight = await self.weight_resolver.resolve_g(title, description, image_url)	# ⚖️ Асинхронне визначення ваги
            data["weight_g"] = int(resolved_weight)						# ⚖️ Зберігаємо вагу у грамах
        except Exception as weight_error:								# noqa: BLE001	# ⚠️ Серйозна помилка резолвера ваги
            logger.warning("⚠️ Помилка визначення ваги: %s", weight_error)	# 🧾 Логуємо попередження
            data["weight_g"] = 0										# 🛟 Повертаємося до нульової ваги

        return data													# 📦 Повертаємо збагачені дані

    # ================================
    # 🏗️ ЗБІРКА ProductInfo
    # ================================
    def _build_product_info(self, data: Dict[str, Any]) -> ProductInfo:
        """
        🏗️ Будує доменну сутність `ProductInfo` з нормалізованими полями.
        """
        stock_aliases = self._load_size_aliases()						# 📚 Підвантажуємо аліаси розмірів
        stock_map = normalize_stock_map(
            data.get("stock_data", {}),
            locale=self.locale,
            aliases=stock_aliases,
        )																# 📦 Нормалізуємо карту наявності
        title = str(data.get("title") or "").strip() or _fallback_title_from_url(self.url)	# 🏷️ Забезпечуємо назву товару

        base_kwargs: Dict[str, Any] = {
            "title": title,											# 🏷️ Заголовок товару
            "price": decimal_from_price_str(data.get("price")),		# 💵 Нормалізована ціна
            "description": str(data.get("description") or ""),		# 📝 Опис товару
            "image_url": str(data.get("main_image") or ""),			# 🖼️ Головне зображення
            "images": tuple(uniq_keep_order(data.get("all_images", []))),	# 🖼️ Унікальні зображення зі збереженням порядку
            "currency": _safe_currency(self._currency_str),			# 💱 Валюта товару
            "sections": freeze(data.get("sections", {})),			# 📚 Заморожені секції опису
            "stock_data": freeze(stock_map),						# 📦 Іммʼютабельна карта наявності
        }															# 🧾 Базові параметри ProductInfo

        weight_value = data.get("weight_g")							# ⚖️ Сира вага товару
        if weight_value is not None:									# ✅ Вага присутня у даних
            try:														# 🛡️ Валідуємо вагу
                info = ProductInfo(**base_kwargs, weight_g=int(weight_value))	# 📦 Повертаємо повний ProductInfo з вагою
                self._log.debug("⚖️ Вага застосована (%s г).", weight_value)
                return info
            except MoneyValueError:	# type: ignore[name-defined]	# ⚠️ Невідповідна грошова величина
                self._log.warning("⚠️ MoneyValueError під час встановлення ваги: %s", weight_value)
            except TypeError:
                self._log.warning("⚠️ TypeError під час встановлення ваги: %s", weight_value)

        info = ProductInfo(**base_kwargs)								# 📦 Повертаємо ProductInfo без ваги
        self._log.debug("🏗️ ProductInfo без ваги (title='%s').", info.title)
        return info

    # ================================
    # ✅ ФІНАЛЬНА ВАЛІДАЦІЯ
    # ================================
    def _validate_info(self, info: ProductInfo) -> ProductInfo:
        """
        ✅ Перевіряє результат і за потреби підставляє безпечні значення.
        """
        title = info.title.strip() if getattr(info, "title", "") else ""	# 🏷️ Очищений заголовок
        safe_title = title or _fallback_title_from_url(self.url)		# 🛟 Фолбек для заголовка

        try:															# 🛡️ Перевіряємо валідність ціни
            _ = +info.price											# 💵 Упевнюємось, що price приводиться до Decimal
            safe_price = info.price									# 💵 Зберігаємо перевірену ціну
        except Exception:	# noqa: BLE001								# ⚠️ Некоректна ціна
            safe_price = Decimal("0.0")								# 🛟 Використовуємо нульову ціну

        base_kwargs: Dict[str, Any] = {
            "title": safe_title,										# 🏷️ Безпечний заголовок
            "price": safe_price,										# 💵 Безпечна ціна
            "description": getattr(info, "description", ""),			# 📝 Опис із джерела
            "image_url": getattr(info, "image_url", ""),				# 🖼️ Посилання на зображення
            "images": tuple(getattr(info, "images", ()) or ()),		# 🖼️ Набір зображень
            "sections": getattr(info, "sections", freeze({})),		# 📚 Структурований опис
            "stock_data": getattr(info, "stock_data", freeze({})),	# 📦 Інформація про наявність
            "currency": getattr(info, "currency", _safe_currency(self._currency_str)),	# 💱 Актуальна валюта
        }																# 🧾 Базові значення для ProductInfo

        weight_value = getattr(info, "weight_g", None)					# ⚖️ Вага товару, якщо є
        if weight_value is not None:									# ✅ Вага присутня
            try:														# 🛡️ Переконуємось у коректності ваги
                return ProductInfo(**base_kwargs, weight_g=int(weight_value))	# 📦 Повертаємо результат із вагою
            except TypeError:											# ⚠️ Неправильний тип ваги
                pass													# 🔁 Повертаємось до fallback

        return ProductInfo(**base_kwargs)								# 📦 Резервний шлях без ваги

    # ================================
    # 📦 ДАНІ ПРО НАЯВНІСТЬ
    # ================================
    def _get_stock_with_fallback(self, extractor: HtmlDataExtractor) -> Dict[str, Dict[str, bool]]:
        """
        📦 Повертає карту наявності: JSON-LD → legacy DOM → пустий dict.
        """
        self._log.debug("📦 Починаємо збір наявності (JSON-LD → legacy).")
        json_ld_stock = extractor.extract_stock_from_json_ld()			# 📦 Дані з JSON-LD
        if json_ld_stock:												# ✅ Дані з JSON-LD знайдено
            self._log.debug("📦 JSON-LD stock успішно використано (%d записів).", len(json_ld_stock))
            return json_ld_stock										# 📦 Повертаємо JSON-LD карту
        legacy_stock = extractor.extract_stock_from_legacy()			# 🏛️ Дані зі старої розмітки
        if legacy_stock:												# ✅ Legacy-дані присутні
            self._log.debug("📦 Використано legacy stock (%d записів).", len(legacy_stock))
            return legacy_stock										# 📦 Повертаємо legacy карту
        self._log.info("📦 Дані про наявність відсутні, повертаємо пусту мапу.")
        return {}														# 🗃️ Порожній словник у разі відсутності даних

    @staticmethod
    def _make_extractor(soup: BeautifulSoup, locale: Optional[str]) -> HtmlDataExtractor:
        """
        🧰 Створює `HtmlDataExtractor` із підтримкою старої сигнатури.
        """
        try:															# 🛡️ Використовуємо нову сигнатуру з locale
            return HtmlDataExtractor(soup, locale=locale)	# type: ignore[call-arg]	# 🧾 Створюємо екстрактор з локаллю
        except TypeError:												# ⚠️ Стара версія без параметра locale
            return HtmlDataExtractor(soup)								# 🧾 Повертаємо екстрактор без локалі

    # ================================
    # 🔧 ХЕЛПЕРИ
    # ================================
    def _make_cache_key(self, url_str: str) -> str:
        """
        🔧 Генерує ключ для HTML-кешу (url або url+region).
        """
        if not self._html_cache_enabled:								# 🚫 Кеш вимкнено → використовуємо URL
            return url_str												# 🔑 Повертаємо вихідний URL

        strategy = self._html_cache_key_strategy						# 🧠 Обрана стратегія формування ключа
        if strategy == "url+region":									# 🌍 Потрібно врахувати регіон
            try:														# 🛡️ Зчитуємо регіон з URL
                region = getattr(self.url_parser_service, "get_region", lambda *_: None)(url_str)	# 🌎 Повертає код регіону
            except Exception:	# noqa: BLE001								# ⚠️ Не вдалося визначити регіон
                region = None											# 🛟 Повертаємося до дефолту
            return f"{url_str}::r={region or ''}"						# 🔑 Додаємо регіон до ключа

        return url_str													# 🔑 Базовий ключ лише з URL

    def _cfg_int(self, key: str, default: int) -> int:
        """
        🔧 Безпечне читання `int` із конфігурації.
        """
        try:															# 🛡️ Зчитуємо значення з конфігурації
            value = self.config_service.get(key, default, cast=int)	# ⚙️ Використовуємо каст до int
            return int(value if value is not None else default)		# 🔢 Нормалізуємо значення
        except Exception:	# noqa: BLE001								# ⚠️ Конфігурація повернула некоректне значення
            return default											# 🛟 Повертаємо дефолт

    def _load_size_aliases(self) -> Dict[str, str]:
        """
        🔧 Завантажує `sizes.aliases` з конфігурації (IMP-056).
        """
        try:															# 🛡️ Отримуємо аліаси з конфігу
            aliases = self.config_service.get("sizes.aliases", {}, dict) or {}	# 📚 Сировинні аліаси
            return {str(key): str(value) for key, value in aliases.items() if value is not None}	# 🧾 Нормалізуємо словник
        except Exception:	# noqa: BLE001								# ⚠️ Помилка читання аліасів
            return {}													# 🛟 Повертаємо порожній словник


# ================================
# 🧰 УТИЛІТИ
# ================================
def _safe_currency(code: Optional[str]) -> Currency:
    """
    🧰 Перетворює рядок у `Currency`, fallback → USD.
    """
    try:																# 🛡️ Намагаємось побудувати валюту
        if not code:													# 🚫 Порожній код валюти
            return Currency.USD										# 💵 Використовуємо USD як дефолт
        return Currency(code)											# 💵 Перетворюємо рядок у Enum
    except Exception:	# noqa: BLE001									# ⚠️ Валюта не підтримується
        return Currency.USD											# 🛟 Повертаємо USD


def _fallback_title_from_url(url: Union[Url, str]) -> str:
    """
    🧰 Формує дефолтний заголовок на основі URL.
    """
    try:																# 🛡️ Створюємо заголовок з URL
        url_str = url.value if isinstance(url, Url) else str(url)		# 🌍 Приводимо універсальний URL
        tail = (url_str or "").rstrip("/").split("/")[-1]				# 🔪 Беремо останню частину шляху
        tail = tail.replace("-", " ").replace("_", " ").strip()			# ✨ Нормалізуємо сегмент
        return tail.capitalize() or "Товар"								# 🏷️ Повертаємо акуратний заголовок
    except Exception:	# noqa: BLE001									# ⚠️ Некоректний URL
        return "Товар"													# 🛟 Повертаємо універсальний fallback
