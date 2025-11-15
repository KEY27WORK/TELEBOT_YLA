# 🧭 src/app/infrastructure/web/webdriver_service.py
"""
🧭 WebDriverService — адаптер Playwright для отримання HTML-сторінок.

🔹 Керує життєвим циклом браузера та контексту.
🔹 Підтримує ретраї, stealth-режим, DevTools та трасування.
🔹 Записує метрики успішності та деградацій.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from playwright.async_api import (									# 🧠 Асинхронний API Playwright
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    Response,
    async_playwright,
)
from playwright_stealth import stealth_async						# 🥷 Прибирає сигнатуру браузера

# 🔠 Системні імпорти
import asyncio														# ⏳ Затримки та корутини
import logging														# 🧾 Логування подій
import re															# 🧪 Регулярні вирази для слагів
from pathlib import Path											# 📁 Робота з директоріями
from typing import Any, Dict, List, Literal, Optional, cast			# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService				# ⚙️ DI-доступ до конфігурацій
from app.domain.web.interfaces import IWebClient					# 🧭 Контракт веб-клієнта
from app.shared.errors import (									# 🚨 Типові помилки веб-доступу
    CloudflareBlockError,
    HttpError,
    InvalidUrlError,
    NetworkError,
    RequestTimeout,
)
from app.shared.metrics.parsing import (							# 📈 Метрики парсингу
    PARSING_FAILURE,
    PARSING_SUCCESS,
)
from app.shared.utils.logger import LOG_NAME						# 🏷️ Базове ім'я логера

logger = logging.getLogger(f"{LOG_NAME}.web")						# 🧾 Ініціалізований логер сервісу


# ================================
# 🏛️ ГОЛОВНИЙ КЛАС
# ================================
class WebDriverService(IWebClient):
    """
    🧭 Реалізація протоколу IWebClient на базі Playwright.
    """

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(self, config_service: ConfigService) -> None:
        """
        🧱 Зчитує налаштування для роботи браузера.

        Args:
            config_service (ConfigService): Джерело конфігурації застосунку.
        """
        self._cfg = config_service										# 🗂️ Зберігаємо постачальника конфігурацій

        self._playwright: Optional[Playwright] = None				# 🧠 Об'єкт Playwright (лінива ініціалізація)
        self._browser: Optional[Browser] = None						# 🌐 Поточний браузер Chromium
        self._context: Optional[BrowserContext] = None				# 🪟 Основний браузерний контекст

        self._is_headless: bool = bool(self._cfg.get("playwright.headless", True))	# 🙈 Режим без інтерфейсу
        self._retry_attempts: int = self._cfg.get("playwright.retry_attempts", 5, cast=int) or 5	# 🔁 Кількість ретраїв
        self._retry_delay_sec: int = self._cfg.get("playwright.retry_delay_sec", 2, cast=int) or 2	# ⏱️ Пауза між ретраями
        self._user_agent: Optional[str] = self._cfg.get("playwright.user_agent")	# 🪪 Глобальний User-Agent

        self._navigation_timeout_ms: int = self._cfg.get(			# ⏳ Таймаут навігації (мс)
            "playwright.navigation_timeout_ms",
            30000,
            cast=int,
        ) or 30000
        self._network_idle_wait_ms: int = self._cfg.get(			# 💤 Додаткова затримка після завантаження
            "playwright.network_idle_wait_ms",
            1500,
            cast=int,
        ) or 1500

        self._enable_stealth: bool = bool(self._cfg.get("playwright.enable_stealth", True))	# 🥷 Чи застосовувати stealth

        raw_phrases: List[str] = self._cfg.get("playwright.cloudflare_phrases", None) or [	# 🧾 Сигнали блокування Cloudflare
            "Your connection needs to be verified",
            "Please complete the security check",
            "Verifying you are human",
            "Checking your browser before accessing",
        ]
        self._cloudflare_phrases: List[str] = [					# ☁️ Нормалізований список тригерів Cloudflare
            str(phrase).strip().lower()
            for phrase in raw_phrases
            if str(phrase).strip()
        ]

        self._trace_enabled: bool = bool(self._cfg.get("playwright.trace.enabled", False))	# 🧵 Чи увімкнуто трасування
        self._trace_mode: str = (									# 🧭 Режим збереження trace-файлів
            self._cfg.get("playwright.trace.mode", "retain-on-failure") or "retain-on-failure"
        ).lower()
        traces_dir = (												# 📁 Базова директорія для trace.zip
            self._cfg.get("playwright.trace.dir")
            or self._cfg.get("files.traces_dir")
            or "./var/traces"
        )
        self._traces_dir: Path = Path(str(traces_dir))			# 🗂️ Шлях до каталогу трас

        self._devtools_enabled: bool = bool(self._cfg.get("playwright.devtools.enabled", False))	# 🛠️ Чи відкривати DevTools
        self._devtools_mode: str = (								# 🪟 Режим DevTools (playwright|cdp)
            self._cfg.get("playwright.devtools.mode", "playwright", cast=str) or "playwright"
        ).lower()
        self._devtools_port: int = int(								# 🔌 Порт для CDP-режиму
            self._cfg.get("playwright.devtools.remote_debugging_port", 0, cast=int) or 0
        )
        self._launch_channel: Optional[str] = self._cfg.get("playwright.launch_channel", None, cast=str)	# 🚀 Канал запуску браузера

        logger.info(
            "✅ WebDriverService: headless=%s, retries=%s, timeout_ms=%s, trace=%s/%s, devtools=%s/%s",
            self._is_headless,
            self._retry_attempts,
            self._navigation_timeout_ms,
            self._trace_enabled,
            self._trace_mode,
            self._devtools_enabled,
            self._devtools_mode,
        )															# 🧾 Фіксуємо підсумкову конфігурацію

    async def __aenter__(self) -> "WebDriverService":
        """
        🤝 Підтримує шаблон async with.

        Returns:
            WebDriverService: Поточний екземпляр після запуску.
        """
        await self.startup()											# 🔌 Гарантуємо, що середовище запущене
        return self													# ↩️ Повертаємо себе для використання у контексті

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """
        🚪 Закриває браузер після виходу з async with.
        """
        await self.shutdown()											# 📴 Завершуємо роботу при виході з контексту

    # ================================
    # 🚪 ПУБЛІЧНИЙ ІНТЕРФЕЙС
    # ================================
    async def startup(self) -> None:
        """
        🔌 Запускає Playwright і Chromium, якщо вони ще не активні.
        """
        if self._browser and self._browser.is_connected():				# 🧪 Перевіряємо, чи браузер уже активний
            return														# ↩️ Уникаємо повторної ініціалізації

        if self._playwright is None:									# 🧠 Запускаємо Playwright за потреби
            self._playwright = await async_playwright().start()		# 🚀 Старт Playwright runtime

        launch_kwargs: Dict[str, Any] = {"headless": self._is_headless}	# 🧰 Базові параметри запуску браузера
        if self._launch_channel:
            launch_kwargs["channel"] = self._launch_channel			# 📺 Вказуємо канал (наприклад, chrome)

        args: List[str] = []											# 📜 Аргументи командного рядка для Chromium

        if self._devtools_enabled:										# 🛠️ Обробляємо режими DevTools
            launch_kwargs["headless"] = False							# 👀 DevTools потребує headful
            if self._devtools_mode == "playwright":
                launch_kwargs["devtools"] = True						# 🧰 Вбудований DevTools Playwright
                logger.info("🛠 DevTools (Playwright) відкриватимуться автоматично.")
            elif self._devtools_mode == "cdp":
                port = max(0, int(self._devtools_port or 0))			# 🔢 Обираємо порт для CDP
                args.append(f"--remote-debugging-port={port}")			# 🔌 Додаємо параметр до запуску
                if port > 0:
                    logger.info("🛠 DevTools (CDP) доступні за адресою http://127.0.0.1:%s", port)
                else:
                    logger.info("🛠 DevTools (CDP) оберуть порт автоматично — перевірте chrome://inspect.")
            else:
                logger.warning("⚠️ Невідомий режим DevTools: %s", self._devtools_mode)

        if args:
            launch_kwargs["args"] = args								# 🧾 Додаємо сформовані аргументи

        logger.info("🚀 Запуск Chromium (headless=%s)…", launch_kwargs.get("headless"))
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)	# 🌐 Старт браузера із параметрами
        self._context = await self._browser.new_context(user_agent=self._user_agent)	# 🪟 Створюємо базовий контекст
        logger.info("✅ Chromium готовий до навігації")

    async def shutdown(self) -> None:
        """
        📴 Завершує сесію браузера та Playwright.
        """
        if self._browser:
            await self._browser.close()								# 🔒 Закриваємо браузер
            self._browser = None										# 🧹 Прибираємо посилання для повторного старту
            self._context = None										# 🧹 Скидаємо контекст
            logger.info("🔒 Chromium закрито")

        if self._playwright:
            await self._playwright.stop()								# 🧯 Зупиняємо Playwright
            self._playwright = None									# 🧹 Звільняємо ресурс
            logger.info("🔌 Playwright зупинено")

    async def get_page_content(
        self,
        url: str,
        *,
        wait_until: Optional[Literal["commit", "domcontentloaded", "load", "networkidle"]] = None,
        timeout_ms: Optional[int] = None,
        retries: Optional[int] = None,
        retry_delay_sec: Optional[int] = None,
        use_stealth: Optional[bool] = None,
        user_agent: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        🌐 Завантажує HTML сторінки з ретраями та записом метрик.

        Args:
            url (str): Посилання для завантаження.
            wait_until (Literal | None): Ціль події для очікування (commit/load/networkidle).
            timeout_ms (int | None): Таймаут навігації у мілісекундах.
            retries (int | None): Кількість спроб.
            retry_delay_sec (int | None): Затримка між спробами у секундах.
            use_stealth (bool | None): Перевизначення stealth-режиму.
            user_agent (str | None): Тимчасовий User-Agent для виклику.
            **kwargs (Any): Додаткові параметри (ігноруються для сумісності).

        Returns:
            Optional[str]: HTML документ або None, якщо всі спроби провалилися.
        """
        if kwargs:
            logger.debug("ℹ️ get_page_content ігнорує додаткові kwargs: %s", kwargs)	# 📝 Логуємо ігноровані параметри

        if not url or not url.startswith(("http://", "https://")):		# 🚦 Перевіряємо коректність URL
            err = InvalidUrlError(url=url, detail="посилання повинно мати http(s)://")	# ❌ Формуємо структуровану помилку
            logger.error("❌ Некоректна адреса: %s", err)
            try:
                PARSING_FAILURE.labels(source="webdriver", reason="invalid_url").inc()	# 📉 Фіксуємо метрику невдачі
            except Exception:
                logger.debug("⚠️ Неможливо інкрементувати метрику invalid_url", exc_info=True)
            return None													# ↩️ Повертаємо None для некоректного URL

        await self.startup()												# 🚀 Переконуємося, що браузер готовий
        page: Optional[Page] = None										# 📄 Поточна сторінка
        temp_ctx: Optional[BrowserContext] = None						# 🧪 Тимчасовий контекст для кастомного UA

        navigation_wait: Literal["commit", "domcontentloaded", "load", "networkidle"] = (
            wait_until or "networkidle"
        )																# 🧭 Подія, на яку чекаємо після переходу
        navigation_timeout_ms = int(timeout_ms or self._navigation_timeout_ms)	# ⏳ Фактичний таймаут навігації
        attempts = int(retries or self._retry_attempts)					# 🔁 Кількість спроб отримання сторінки
        retry_delay = int(retry_delay_sec or self._retry_delay_sec)		# ⏱️ Пауза між спробами
        stealth_enabled = self._enable_stealth if use_stealth is None else bool(use_stealth)	# 🥷 Режим stealth для сторінки

        for attempt in range(1, attempts + 1):							# 🔁 Ітеруємося за кількістю спроб
            tracing_started = False										# 🧵 Маркер активного трасування
            try:
                if not self._browser:
                    raise RuntimeError("Browser not initialized")		# 🚨 Захист від некоректного стану
                if not self._context:
                    raise RuntimeError("BrowserContext not initialized")	# 🚨 Контекст має існувати

                ctx: BrowserContext										# 🪟 Контекст для поточної спроби
                if user_agent:
                    temp_ctx = await self._browser.new_context(user_agent=user_agent)	# 🧪 Створюємо тимчасовий контекст
                    ctx = temp_ctx										# 🔄 Використовуємо його для навігації
                    logger.debug("🧪 Використано тимчасовий User-Agent для поточного виклику.")
                else:
                    ctx = cast(BrowserContext, self._context)			# 🔁 Повертаємося до базового контексту

                if self._trace_enabled:
                    try:
                        await self._ensure_traces_dir()					# 🗂️ Готуємо директорію для trace
                        await ctx.tracing.start(						# 📼 Запускаємо запис трас
                            screenshots=True,
                            snapshots=True,
                            sources=True,
                        )
                        tracing_started = True							# 🧵 Позначаємо, що трасування активне
                    except Exception as trace_err:
                        logger.debug("⚠️ Не вдалося стартувати трасування: %s", trace_err)

                page = await ctx.new_page()								# 📄 Відкриваємо нову сторінку
                if stealth_enabled:
                    await stealth_async(page)							# 🥷 Ховаємо ознаки автоматизації

                logger.info("🌍 Завантаження %s (%s/%s)", url, attempt, attempts)
                response: Optional[Response] = await page.goto(			# 🌐 Виконуємо перехід за адресою
                    url,
                    wait_until=navigation_wait,
                    timeout=navigation_timeout_ms,
                )

                if self._network_idle_wait_ms > 0:
                    await asyncio.sleep(self._network_idle_wait_ms / 1000)	# 💤 Чекаємо остаточного завантаження

                status_code = response.status if response else None		# 🔢 Перевіряємо HTTP-статус
                if status_code in (403, 429, 502):
                    err = HttpError(url=url, status_code=int(status_code), detail="тимчасова помилка")	# 🚨 Тимчасова помилка
                    logger.warning("⚠️ HTTP %s → повтор через %s с (%s)", status_code, retry_delay, err)
                    try:
                        PARSING_FAILURE.labels(source="webdriver", reason=f"http_{status_code}").inc()	# 📉 Відмічаємо невдачу
                    except Exception:
                        logger.debug("⚠️ Неможливо інкрементувати метрику http_%s", status_code, exc_info=True)
                    await self._maybe_export_trace(
                        ctx,
                        url,
                        attempt,
                        success=False,
                        is_final=(attempt == attempts),
                        tracing_started=tracing_started,
                    )													# 🧵 Зберігаємо трасу при потребі
                    await asyncio.sleep(retry_delay)					# ⏱️ Чекаємо перед наступною спробою
                    continue												# 🔁 Переходимо до нової спроби

                html = await page.content()								# 📃 Отримуємо HTML сторінки
                if self._is_blocked_by_cloudflare(html):
                    err = CloudflareBlockError(url=url)				# ☁️ Фіксуємо блокування Cloudflare
                    logger.warning("⚠️ Cloudflare блокує доступ (%s) → повтор через %s с", err, retry_delay)
                    try:
                        PARSING_FAILURE.labels(source="webdriver", reason="cloudflare").inc()	# 📉 Відмічаємо блокування
                    except Exception:
                        logger.debug("⚠️ Неможливо інкрементувати метрику cloudflare", exc_info=True)
                    await self._maybe_export_trace(
                        ctx,
                        url,
                        attempt,
                        success=False,
                        is_final=(attempt == attempts),
                        tracing_started=tracing_started,
                    )													# 🧵 Зберігаємо трасу при невдачі
                    await asyncio.sleep(retry_delay)					# ⏱️ Чекаємо перед наступним опитуванням
                    continue												# 🔁 Пробуємо знову

                try:
                    PARSING_SUCCESS.labels(source="webdriver").inc()	# 📈 Фіксуємо успішне завантаження
                except Exception:
                    logger.debug("⚠️ Неможливо інкрементувати метрику успішного парсингу", exc_info=True)

                await self._maybe_export_trace(
                    ctx,
                    url,
                    attempt,
                    success=True,
                    is_final=True,
                    tracing_started=tracing_started,
                )														# 🧵 Зберігаємо трасу, якщо потрібно
                return html												# ✅ Повертаємо HTML документ

            except PlaywrightError as exc:
                detail = str(exc)										# 🧾 Текст помилки
                if "timeout" in detail.lower():
                    err = RequestTimeout(
                        url=url,
                        timeout_ms=navigation_timeout_ms,
                        detail=detail,
                    )													# ⏳ Перетворюємо на типізований timeout
                    metric_reason = "timeout"							# 🧭 Мітка для метрик
                else:
                    err = NetworkError(url=url, detail=detail)			# 🌐 Будь-яка інша мережна помилка
                    metric_reason = "playwright_error"					# 🧭 Альтернативна мітка

                logger.warning("❌ Playwright (%s/%s): %s", attempt, attempts, err)
                try:
                    PARSING_FAILURE.labels(source="webdriver", reason=metric_reason).inc()	# 📉 Фіксуємо невдачу
                except Exception:
                    logger.debug("⚠️ Неможливо інкрементувати метрику %s", metric_reason, exc_info=True)

                ctx_for_trace: BrowserContext = temp_ctx or cast(BrowserContext, self._context)	# 🧵 Контекст для інциденту
                await self._maybe_export_trace(
                    ctx_for_trace,
                    url,
                    attempt,
                    success=False,
                    is_final=(attempt == attempts),
                    tracing_started=tracing_started,
                )														# 🧵 Зберігаємо трасу при помилці
                await asyncio.sleep(retry_delay)						# ⏱️ Пауза перед наступною спробою

            finally:
                if page:
                    try:
                        if not page.is_closed():
                            await page.close()							# 🔒 Акуратно закриваємо вкладку
                    except Exception as close_err:						# noqa: BLE001
                        logger.debug("ℹ️ Не вдалося закрити вкладку: %s", close_err)
                    page = None											# 🧹 Скидаємо посилання

                if temp_ctx:
                    try:
                        await temp_ctx.close()							# 🧹 Закриваємо тимчасовий контекст
                    except Exception:
                        logger.debug("⚠️ Не вдалося закрити тимчасовий контекст", exc_info=True)
                    temp_ctx = None										# 🧹 Очищаємо посилання

        logger.error("❌ Вичерпано %s спроб для %s", attempts, url)
        return None														# ↩️ Повертаємо None після всіх невдач

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _is_blocked_by_cloudflare(self, html: str) -> bool:
        """
        🛡️ Визначає, чи контент заблоковано Cloudflare.

        Args:
            html (str): HTML код сторінки.

        Returns:
            bool: True, якщо знайдено ознаки блокування.
        """
        if not html:
            return False												# ↩️ Порожній HTML не вважаємо блокуванням

        body = html.lower()											# 🔡 Нормалізуємо контент для пошуку фраз
        if any(phrase in body for phrase in self._cloudflare_phrases):
            return True												# ✅ Знайдено ключові фрази блокування
        if "<title>just a moment...</title>" in body:
            return True												# ✅ Класичний splash Cloudflare
        return False													# ↩️ Інакше блокування нема

    async def _maybe_export_trace(
        self,
        ctx: BrowserContext,
        url: str,
        attempt: int,
        *,
        success: bool,
        is_final: bool,
        tracing_started: bool,
    ) -> None:
        """
        🧵 Зберігає трасу Playwright залежно від конфігурації.

        Args:
            ctx (BrowserContext): Контекст, з якого збиралася траса.
            url (str): Цільова адреса.
            attempt (int): Номер спроби.
            success (bool): Ознака успішного результату.
            is_final (bool): Чи це фінальна спроба.
            tracing_started (bool): Чи було активовано трасування.
        """
        if not self._trace_enabled or not tracing_started:
            return														# ↩️ Нічого зберігати

        should_save = False											# 🧭 Рішення щодо збереження
        if self._trace_mode == "on":
            should_save = True										# 💾 Зберігаємо завжди
        elif self._trace_mode == "retain-on-failure":
            should_save = (not success) and is_final					# 💾 Лишаємо тільки на останній невдачі

        try:
            if should_save:
                await self._ensure_traces_dir()						# 🗂️ Переконуємося, що директорія існує
                path = self._make_trace_path(url, attempt, success=success)	# 🗺️ Формуємо шлях для trace.zip
                await ctx.tracing.stop(path=str(path))					# 💾 Зберігаємо трасу у файл
                logger.info("🧵 Трасу збережено: %s", path)
            else:
                await ctx.tracing.stop()								# 🧹 Просто зупиняємо запис без файлу
        except Exception as trace_err:
            logger.debug("⚠️ Проблема зі збереженням trace: %s", trace_err)

    async def _ensure_traces_dir(self) -> None:
        """
        📁 Створює директорію для trace-файлів.
        """
        try:
            self._traces_dir.mkdir(parents=True, exist_ok=True)		# 🧱 Створюємо шлях при необхідності
        except Exception as dir_err:
            logger.debug("⚠️ Не вдалося створити теку traces: %s", dir_err)

    def _make_trace_path(self, url: str, attempt: int, *, success: bool) -> Path:
        """
        🗂️ Формує шлях до trace.zip.

        Args:
            url (str): Джерельний URL.
            attempt (int): Номер спроби.
            success (bool): Ознака успіху.

        Returns:
            Path: Повний шлях до файлу trace.zip.
        """
        slug = self._slugify_url(url)									# 🔤 Перетворюємо URL у придатний слаг
        suffix = "ok" if success else "fail"							# 🏷️ Позначка успіху/невдачі
        filename = f"{slug}__try{attempt:02d}__{suffix}.zip"			# 🧾 Ім'я trace-файлу
        return self._traces_dir / filename								# 📁 Повертаємо повний шлях

    @staticmethod
    def _slugify_url(url: str) -> str:
        """
        🔤 Перетворює URL у безпечний для файлової системи формат.

        Args:
            url (str): Оригінальний URL.

        Returns:
            str: Очищений слаг.
        """
        try:
            without_proto = re.sub(r"^https?://", "", url.strip(), flags=re.IGNORECASE)	# ✂️ Прибираємо протокол
            without_query = without_proto.split("?")[0]				# 🧮 Відкидаємо query-параметри
            slug = re.sub(r"[^a-zA-Z0-9._\-/]", "_", without_query)	# 🧼 Замінюємо заборонені символи
            slug = slug.strip("/").replace("/", "__")					# 🔧 Робимо слаг без слешів
            return slug[:160] if len(slug) > 160 else slug or "trace"	# 📏 Обмежуємо довжину
        except Exception:
            return "trace"												# ↩️ Запасний варіант при помилці
