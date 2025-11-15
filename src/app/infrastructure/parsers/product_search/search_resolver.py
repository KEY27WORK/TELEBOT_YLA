# 🔍 app/infrastructure/parsers/product_search/search_resolver.py
"""
🔍 ProductSearchResolver — асинхронний UI-пошук товарів YoungLA через Playwright.

🔹 Відкриває сайт, ініціює діалог пошуку та збирає посилання з predictive/повної видачі.
🔹 Підтримує конфігурацію через overrides → ParserInfraOptions → ConfigService → дефолти.
🔹 Логує всі значущі кроки українською, спрощуючи діагностику headless-пошуку.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright	# 🕹️ Playwright API

# 🔠 Системні імпорти
import asyncio	# ⏱️ Retry-бекофф
import logging	# 🧾 Логування сценаріїв
from typing import Final, List, Optional, Sequence, Tuple, cast	# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService	# ⚙️ Конфіги
from app.domain.products.entities import Url	# 📦 Доменний URL
from app.domain.products.interfaces import (	# 🤝 Контракти провайдера пошуку
    IProductSearchProvider,
    SEARCH_DEFAULT_LIMIT,
    SEARCH_MAX_LIMIT,
    SearchResult,
)
from app.infrastructure.parsers._infra_options import ParserInfraOptions	# 🧱 Інфра-налаштування
from app.shared.utils.logger import LOG_NAME	# 🏷️ Базове імʼя логера

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.parsers.search_resolver")	# 🧾 Іменований логер модуля


# ================================
# 🏛️ ПОШУКОВИЙ РЕЗОЛВЕР
# ================================
class ProductSearchResolver(IProductSearchProvider):
    """🏛️ Надійний UI-пошук товарів youngla.com із керованими таймаутами."""

    BASE_URL: Final[str] = "https://www.youngla.com"	# 🌍 Базовий домен

    DEFAULT_GOTO_TIMEOUT_MS: Final[int] = 30_000	# ⏱️ DOM завантаження
    DEFAULT_IDLE_TIMEOUT_MS: Final[int] = 15_000	# ⏱️ Очікування networkidle
    DEFAULT_PREDICTIVE_TIMEOUT_MS: Final[int] = 7_000	# ⚡ Predictive-підказки
    DEFAULT_MAX_RESULTS: Final[int] = 10	# 📄 Дефолт кількості результатів
    DEFAULT_MAX_RESULTS_HARDCAP: Final[int] = 30	# 📄 Жорсткий верхній ліміт
    DEFAULT_RETRY_ATTEMPTS: Final[int] = 2	# 🔁 Спроби пошуку
    DEFAULT_RETRY_BACKOFF_MS: Final[int] = 600	# ⏱️ Початковий бекофф

    OPEN_SEARCH_CANDIDATES: Final[Tuple[str, ...]] = (
        'a[href="/search"]',
        'a[aria-controls^="header-search"]',
        'button[aria-controls^="header-search"]',
        'button[aria-label*="Open search" i]',
    )	# 🖱️ Потенційні тригери відкриття діалогу

    SEARCH_DIALOG: Final[str] = "header-search[open]"	# 🪟 Відкритий діалог
    SEARCH_FORM: Final[str] = "form#predictive-search-form.header-search__form"	# 🧾 Форма пошуку
    SEARCH_INPUT: Final[str] = 'input[type="search"][name="q"].header-search__input'	# ⌨️ Поле введення

    PREDICTIVE_ROOT: Final[str] = "predictive-search#header-predictive-search"	# ⚡ Контейнер підказок
    PREDICTIVE_FIRST_PRODUCT_LINKS: Final[Tuple[str, ...]] = (
        f"{PREDICTIVE_ROOT} .predictive-search__products a.product-card__media",
        f"{PREDICTIVE_ROOT} .predictive-search__products a.product-title",
        f"{PREDICTIVE_ROOT} .horizontal-product-card a.horizontal-product-card__figure",
        f"{PREDICTIVE_ROOT} .horizontal-product-card a.product-title",
        f"{PREDICTIVE_ROOT} a[href*='/products/']",
    )	# ⚡ Селектори перших результатів

    VIEW_ALL_RESULTS_BTN: Final[str] = 'button[form="predictive-search-form"]'	# 📎 Кнопка переходу на повну видачу

    RESULTS_FIRST_LINKS: Final[Tuple[str, ...]] = (
        "main a.product-card__media",
        "main a.product-title",
        "main .horizontal-product-card a.horizontal-product-card__figure",
        "main .horizontal-product-card a.product-title",
        "main a[href*='/products/']",
        "a[href*='/products/']",
    )	# 📄 Селектори для повної сторінки

    def __init__(
        self,
        webdriver_service=None,	# 🧩 Зарезервовано для майбутньої інтеграції
        url_parser_service=None,
        config_service: Optional[ConfigService] = None,
        *,
        goto_timeout_ms: Optional[int] = None,	# ⏱️ Локальні override-и
        idle_timeout_ms: Optional[int] = None,
        predictive_timeout_ms: Optional[int] = None,
        max_results_default: Optional[int] = None,
        max_results_hardcap: Optional[int] = None,
        retry_attempts: Optional[int] = None,
        retry_backoff_ms: Optional[int] = None,
        infra_options: Optional[ParserInfraOptions] = None,	# 🧾 Єдині опції інфри
    ) -> None:
        self._webdriver_service = webdriver_service	# 🕹️ Зберігаємо сервіс браузера
        self._url_parser_service = url_parser_service	# 🔗 Сервіс нормалізації URL
        self._cfg = config_service	# ⚙️ Джерело конфігів
        self._opts = infra_options	# 🧱 Інфра-опції (може бути None)

        def _cfg_int(key: str, default_val: int) -> int:
            """🗂️ Безпечно зчитує int із ConfigService."""
            if not self._cfg:	# 🪣 Конфіг відсутній
                return default_val
            try:
                value = self._cfg.get(key, default_val, cast=int) or default_val	# 🧾 Зчитуємо значення
                return int(value)	# 🔢 Повертаємо int
            except Exception as exc:	# ⚠️ Некоректне значення
                logger.debug("⚠️ ConfigService key '%s' недоступний: %s", key, exc)	# 🪵 Повідомляємо
                return default_val	# 🪣 Віддаємо дефолт

        def _pick(name_in_opts: str, cfg_key: str, default_val: int, override_val: Optional[int]) -> int:
            """🧮 Визначає фінальне значення з пріоритетом overrides → opts → config → default."""
            if override_val is not None:	# ✅ Прямий override
                return int(override_val)
            if self._opts is not None and hasattr(self._opts, name_in_opts):	# 🧾 Перевіряємо опції
                candidate = getattr(self._opts, name_in_opts)	# 🔍 Дістаємо значення
                if isinstance(candidate, int) and candidate > 0:	# ✅ Валідний int
                    return int(candidate)
            return int(_cfg_int(cfg_key, default_val))	# 📥 Падаємо у конфіг/дефолт

        self._goto_timeout_ms = _pick("search_goto_timeout_ms", "search.goto_timeout_ms", self.DEFAULT_GOTO_TIMEOUT_MS, goto_timeout_ms)	# ⏱️ Таймаут goto
        self._idle_timeout_ms = _pick("search_idle_timeout_ms", "search.idle_timeout_ms", self.DEFAULT_IDLE_TIMEOUT_MS, idle_timeout_ms)	# ⏱️ Idle
        self._predictive_timeout_ms = _pick("search_predictive_timeout_ms", "search.predictive_timeout_ms", self.DEFAULT_PREDICTIVE_TIMEOUT_MS, predictive_timeout_ms)	# ⚡ Predictive
        self._max_results_default = _pick("search_max_results_default", "search.max_results_default", self.DEFAULT_MAX_RESULTS, max_results_default)	# 📄 Дефолт ліміту
        self._max_results_hardcap = _pick("search_max_results_hardcap", "search.max_results_hardcap", self.DEFAULT_MAX_RESULTS_HARDCAP, max_results_hardcap)	# 📄 Hardcap
        self._retry_attempts = _pick("search_retry_attempts", "search.retry_attempts", self.DEFAULT_RETRY_ATTEMPTS, retry_attempts)	# 🔁 Ретраї
        self._retry_backoff_ms = _pick("search_retry_backoff_ms", "search.retry_backoff_ms", self.DEFAULT_RETRY_BACKOFF_MS, retry_backoff_ms)	# ⏱️ Бекофф

        self._ua_override = getattr(self._opts, "user_agent", None) if self._opts else None	# 🕵️ Кастомний UA
        self._locale_override = getattr(self._opts, "locale", None) if self._opts else None	# 🌍 Кастомна локаль
        logger.debug(
            "🔍 ProductSearchResolver ініціалізовано (goto=%s idle=%s predictive=%s max_def=%s max_cap=%s)",
            self._goto_timeout_ms,
            self._idle_timeout_ms,
            self._predictive_timeout_ms,
            self._max_results_default,
            self._max_results_hardcap,
        )	# 🪵 Параметри інстансу

    # ================================
    # 🤝 ІНТЕРФЕЙС ДОМЕННОГО ПРОВАЙДЕРА
    # ================================
    async def resolve_one(self, query: str) -> Optional[Url]:
        """🔍 Повертає перший знайдений товар як `Url` або `None`."""
        href = await self._search_first_href(query)	# 🔗 Шукаємо одиночне посилання
        result_url = Url(self._canonicalize(href)) if href else None	# 🏷️ Канонізуємо URL
        logger.info("🔍 resolve_one завершено (query='%s' found=%s)", query, bool(result_url))	# 🪵 Статистика
        return result_url	# 🔁 Повертаємо результат

    async def resolve_many(self, query: str, limit: int = SEARCH_DEFAULT_LIMIT) -> List[SearchResult]:
        """📚 Повертає до `limit` результатів у форматі `SearchResult`."""
        if not limit or limit <= 0:	# 🧮 Невалідний ліміт
            limit = self._max_results_default	# 📄 Фіксуємо дефолт
        safe_limit = min(max(1, int(limit)), int(min(SEARCH_MAX_LIMIT, self._max_results_hardcap)))	# 🛡️ Обмежуємо
        links = await self._search_many_with_retries(query, safe_limit)	# 🔁 Виконуємо пошук із ретраями
        results = [SearchResult(url=Url(self._canonicalize(href)), title=None, score=1.0) for href in links]	# 📦 Будуємо DTO
        logger.info("📚 resolve_many: query='%s' requested=%s returned=%s", query, limit, len(results))	# 🪵 Статистика
        return results	# 🔁 Повертаємо список

    @classmethod
    async def resolve(cls, query: str) -> Optional[str]:
        """♻️ Back-compat: повертає лише перший URL як рядок, використовуючи дефолтні таймінги."""
        temp_instance = cls()	# 🧱 Тимчасовий екземпляр
        links = await temp_instance._search_many_impl(query, 1)	# 🔍 Шукаємо один результат
        return links[0] if links else None	# 🔁 Повертаємо рядок або None

    # ================================
    # 🔁 RETRY-КОНТУР
    # ================================
    async def _search_many_with_retries(self, query: str, limit: int) -> List[str]:
        """🔁 Виконує пошук із експоненційним бекоффом і повторними спробами."""
        attempts = max(0, int(self._retry_attempts))	# 🔢 Кількість спроб
        backoff = max(1, int(self._retry_backoff_ms))	# ⏱️ Початковий бекофф, мс
        for attempt in range(attempts + 1):	# 🔁 Спробуємо N+1 разів
            try:
                return await self._search_many_impl(query, limit)	# ✅ Успішний пошук
            except asyncio.CancelledError:
                raise
            except Exception as exc:	# ⚠️ Спроба не вдалася
                logger.warning(
                    "⚠️ Пошук '%s' спроба %s/%s завершилася збоєм: %s",
                    query,
                    attempt + 1,
                    attempts + 1,
                    exc,
                )	# 🪵 Лог помилки
                if attempt >= attempts:	# 🚫 Вичерпали спроби
                    break
                await asyncio.sleep(backoff / 1000.0)	# 💤 Чекаємо перед наступною спробою
                backoff *= 2	# 📈 Експоненційно збільшуємо бекофф
        logger.error("❌ Пошук '%s' провалено після %s спроб.", query, attempts + 1)	# 🧨 Кінцевий збій
        return []	# 🪣 Немає результатів

    # ================================
    # 🧠 ОСНОВНА ЛОГІКА ПОШУКУ
    # ================================
    async def _search_first_href(self, query: str) -> Optional[str]:
        """🔗 Повертає перший посилання-результат (або None)."""
        links = await self._search_many_impl(query, 1)	# 🔍 Шукаємо один результат
        return links[0] if links else None	# 🔁 Віддаємо рядок

    async def _search_many_impl(self, raw_query: str, limit: int) -> List[str]:
        """🧠 Основний сценарій Playwright-пошуку з predictive та повною видачею."""
        query = self._sanitize_query(raw_query)	# 🧼 Очищаємо запит
        logger.info("🔍 YLA search стартував: query='%s' limit=%s", query, limit)	# 🪵 Стартовий лог

        async with async_playwright() as playwright:	# 🕹️ Створюємо Playwright-контекст
            browser = await playwright.chromium.launch(headless=True)	# 🧠 Запускаємо браузер
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},	# 🖥️ Розмір вікна
                user_agent=self._ua_override
                or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),	# 🕵️ UA по замовчуванню
                locale=self._locale_override or "en-US",	# 🌍 Локаль браузера
            )
            page = await context.new_page()	# 📄 Нова вкладка
            try:
                await self._goto(page, self.BASE_URL)	# 🌐 Відкриваємо головну
                await self._open_search(page)	# 🖱️ Відкриваємо діалог пошуку
                await page.fill(self.SEARCH_INPUT, "")	# 🧼 Очищаємо поле вводу
                await page.fill(self.SEARCH_INPUT, query)	# ⌨️ Вводимо запит

                predictive_links = await self._collect_first_hrefs(
                    page,
                    self.PREDICTIVE_FIRST_PRODUCT_LINKS,
                    limit,
                    self._predictive_timeout_ms,
                )	# ⚡ Збираємо predictive
                if predictive_links:	# ✅ Знайшли в підказках
                    logger.info("⚡ Predictive-пошук повернув %s результатів.", len(predictive_links))	# 🪵 Лог
                    return predictive_links	# 🔁 Повертаємо список

                await self._open_full_results(page)	# 📄 Переходимо на повну видачу
                return await self._collect_first_hrefs(
                    page,
                    self.RESULTS_FIRST_LINKS,
                    limit,
                    self._idle_timeout_ms,
                )	# 📄 Повертаємо результати зі сторінки

            except asyncio.CancelledError:
                raise
            except PlaywrightTimeoutError:	# ⏱️ Таймаут Playwright
                logger.exception("⏱️ YoungLA search timeout (query='%s').", query)	# 🪵 Лог
                return []	# 🪣 Без результатів
            except Exception as exc:	# ⚠️ Інші збої
                logger.exception("💥 YoungLA search fatal error: %s", exc)	# 🪵 Повний traceback
                return []	# 🪣 Порожній список
            finally:
                for closer in (page.close, context.close, browser.close):	# 🧹 Закриваємо ресурси
                    try:
                        await closer()	# 🧼 Закриття
                    except Exception:
                        continue

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    async def _goto(self, page: Page, url: str) -> None:
        """🌐 Навігація з fallback на `wait_until="commit"` при затримках."""
        try:
            await page.goto(url, timeout=self._goto_timeout_ms, wait_until="domcontentloaded")	# 🌐 DOM event
        except PlaywrightTimeoutError:	# ⚠️ DOM не настав
            logger.warning("⚠️ DOM не дочекався, fallback на 'commit'.")	# 🪵 Попереджаємо
            await page.goto(url, timeout=self._goto_timeout_ms, wait_until="commit")	# 🌐 Мінімальний лоад

        for state in ("domcontentloaded", "networkidle"):	# 🔁 Дочікуємо стани
            try:
                await page.wait_for_load_state(state, timeout=self._idle_timeout_ms)	# ⏱️ Чекаємо
            except PlaywrightTimeoutError:	# ⚠️ Стейт не настав
                logger.debug("⏱️ Очікування стану %s перевищило таймаут.", state)	# 🪵 Повідомляємо
                continue

    async def _open_search(self, page: Page) -> None:
        """🖱️ Клікає перший доступний тригер пошуку та очікує діалог."""
        for selector in self.OPEN_SEARCH_CANDIDATES:	# 🔁 Перебираємо тригери
            try:
                await page.wait_for_selector(selector, timeout=8_000, state="attached")	# ⏱️ Чекаємо появи
                await page.evaluate("sel => document.querySelector(sel)?.click()", selector)	# 🖱️ Клікаємо JS
                break	# ✅ Відкрито
            except PlaywrightTimeoutError:	# ⚠️ Тригер не знайдено
                continue
        await page.wait_for_selector(self.SEARCH_DIALOG, timeout=8_000, state="visible")	# 🪟 Чекаємо діалог
        await page.wait_for_selector(self.SEARCH_INPUT, timeout=8_000)	# ⌨️ Чекаємо input

    async def _collect_first_hrefs(
        self,
        page: Page,
        selectors: Sequence[str],
        limit: int,
        wait_timeout_ms: int,
    ) -> List[str]:
        """🔗 Повертає до `limit` унікальних абсолютних посилань за набором селекторів."""
        if not selectors:	# 🪣 Порожній набір
            return []
        try:
            if self.PREDICTIVE_ROOT in selectors[0]:
                await page.wait_for_selector(self.PREDICTIVE_ROOT, timeout=wait_timeout_ms)	# ⚡ Чекаємо підказки
        except PlaywrightTimeoutError:	# ⚠️ Підказки не зʼявилися
            return []

        links: List[str] = []	# 📦 Результати
        seen: set[str] = set()	# ♻️ Запобігаємо дублям
        for selector in selectors:	# 🔁 Перебираємо селектори
            if len(links) >= limit:	# ✅ Досягли ліміту
                break
            try:
                for element in await page.query_selector_all(selector):	# 🔍 Усі збіги
                    href = (await element.get_attribute("href")) or ""	# 🔗 Читаємо href
                    if not href:
                        continue
                    absolute = self._abs(href)	# 🌐 Робимо абсолютним
                    if absolute and absolute not in seen:
                        seen.add(absolute)	# ♻️ Запамʼятовуємо
                        links.append(absolute)	# 📦 Додаємо до результатів
                        if len(links) >= limit:
                            break
            except PlaywrightTimeoutError:
                continue
        return links

    async def _open_full_results(self, page: Page) -> None:
        """📄 Переходить на повну сторінку результатів (кнопка або submit)."""
        try:
            if await page.locator(self.VIEW_ALL_RESULTS_BTN).count():	# 🖱️ Є кнопка «View All»
                try:
                    await page.click(self.VIEW_ALL_RESULTS_BTN)	# 🖱️ Клікаємо
                except Exception:
                    await page.locator(self.SEARCH_FORM).evaluate("form => form.submit()")	# 📤 Submit форми
            else:
                if await page.locator(self.SEARCH_FORM).count():	# 🧾 Форма на місці
                    await page.locator(self.SEARCH_FORM).evaluate("form => form.submit()")	# 📤 Submit
                else:
                    await page.press(self.SEARCH_INPUT, "Enter")	# ⌨️ Enter
        except Exception as exc:
            logger.debug("⚠️ Неможливо відкрити повні результати: %s", exc)	# 🪵 Нефатально

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=self._idle_timeout_ms)	# ⏱️ DOM
            await page.wait_for_load_state("networkidle", timeout=self._idle_timeout_ms)	# ⏱️ Network idle
        except PlaywrightTimeoutError:
            logger.debug("⚠️ Стани завантаження повної сторінки пошуку не дочекались.")	# 🪵 Попередження

        html = (await page.content()).lower()	# 🧼 Отримуємо HTML
        if "captcha" in html or "are you human" in html:	# 🛑 Блокування
            raise PlaywrightTimeoutError("blocked by captcha")	# ❌ Генеруємо таймаут

    # ================================
    # ♻️ КАНОНІЗАЦІЯ URL ТА ЗАПИТУ
    # ================================
    @staticmethod
    def _sanitize_query(raw: str) -> str:
        """🧼 Обрізає пробіли та обмежує довжину запиту 120 символами."""
        query = (raw or "").strip()	# 🧼 Тримінг
        return query[:120] if len(query) > 120 else query	# ✂️ Обмеження

    def _canonicalize(self, href: str) -> str:
        """🔗 Нормалізує href через `_url_parser_service` (якщо доступний)."""
        absolute = self._abs(href)	# 🌐 Робимо абсолютним
        try:
            normalize = getattr(self._url_parser_service, "normalize", None)	# 🔍 Шукаємо метод
            if callable(normalize):
                normalized = normalize(absolute)	# 🧮 Нормалізація
                if normalized:
                    absolute = str(normalized)	# 🔁 Оновлюємо
        except Exception as exc:
            logger.debug("⚠️ Неможливо канонізувати URL '%s': %s", href, exc)	# 🪵 Уточнюємо
        return absolute	# 🔁 Повертаємо

    @staticmethod
    def _abs(href: str) -> str:
        """🌐 Перетворює відносний href у абсолютний URL сайту."""
        if not href:	# 🪣 Порожнє значення
            return ""
        trimmed = href.strip()	# 🧼 Прибираємо пробіли
        if trimmed.startswith("//"):	# 🌐 Протокол-агностичні посилання
            return f"https:{trimmed}"
        if trimmed.startswith("/"):	# 🏠 Відносний шлях
            return ProductSearchResolver.BASE_URL.rstrip("/") + trimmed
        return trimmed	# 🔁 Уже абсолютний
