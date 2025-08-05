# 🧭 app/infrastructure/web/webdriver_service.py
"""
🧭 webdriver_service.py — керування браузером через Playwright для парсингу YoungLA.

🔹 Клас `WebDriverService`:
- Працює через один спільний екземпляр браузера (shared singleton).
- Надає методи для отримання HTML-коду або чистої сторінки для взаємодії.
- Має конфігурований режим headless для зручного налагодження.
- Стабільно працює з Cloudflare завдяки логіці повторних спроб.

Використовує:
- playwright.async_api — асинхронний API для браузера Chromium
- playwright_stealth — для обходу Cloudflare
- logging — для логування та дебагу
"""

# 🔠 Системні імпорти
import logging 													    # 🧾 Логування
import asyncio 													    # 🔄 Асинхронна затримка
from typing import Optional, List								    # 📐 Типи для змінних та методів

# 🌐 Зовнішні бібліотеки
from playwright.async_api import ( 
	async_playwright, 												# 🚀 Запуск Playwright API
	Playwright, 													# 🧠 Обʼєкт Playwright
	Browser, 														# 🌍 Браузер Chromium
	BrowserContext, 												# 🔒 Контекст (cookies, UA)
	Page, 															# 📄 Вкладка браузера
	Error as PlaywrightError 										# 🧨 Обробка помилок Playwright
)
from playwright_stealth import stealth_async					    # 🥷 Обхід захисту

# 🧩 Внутрішні модулі
from app.config.config_service import ConfigService			        # ⚙️ Конфіг сервіс
from app.shared.utils.logger import LOG_NAME					    # 📒 Імʼя логера

logger = logging.getLogger(LOG_NAME)

# ==============================
# 🌐 КЛАС КЕРУВАННЯ БРАУЗЕРОМ
# ==============================
class WebDriverService:
	"""
	🧭 Відповідає за завантаження HTML-контенту з сайту через Playwright.
	Підтримує асинхронний контекстний менеджер для зручного використання.
	"""

	def __init__(self, config_service: ConfigService):
		"""
		⚙️ Ініціалізація сервісу з впровадженням залежностей.
		"""
		self._config = config_service														            # ⚙️ Зовнішня конфігурація (DI)
		self._playwright: Optional[Playwright] = None								                    # 🔁 Shared runner
		self._browser: Optional[Browser] = None										                    # 🌍 Chromium browser
		self._context: Optional[BrowserContext] = None								                    # 🔒 Browser context

		# 🔁 Конфігуровані параметри з fallback
		self._is_headless: bool = self._config.get("playwright.headless", True)			                # 🧊 Чи запускати без UI
		self._retry_attempts: int = self._config.get("playwright.retry_attempts", 5)	                # 🔁 Кількість повторів при помилці
		self._retry_delay_sec: int = self._config.get("playwright.retry_delay_sec", 2)	                # ⏱️ Затримка між спробами

		# 🛡️ Перевірка Cloudflare (налаштовується через конфіг)
		self._cloudflare_phrases: List[str] = self._config.get(
			"playwright.cloudflare_phrases",
			[
				"Your connection needs to be verified",
				"Please complete the security check",
				"Verifying you are human"
			]
		)
		logger.info("✅ WebDriverService створено.")

	async def __aenter__(self):
		"""🔛 Ініціалізує браузер при вході в контекст."""
		await self._init_browser()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""🔚 Закриває браузер при виході з контексту."""
		await self.close_browser()

	async def _init_browser(self):
		"""
		🚀 Ініціалізує браузер і контекст, якщо вони ще не створені.
		🔁 Повторно використовується між запитами (shared instance)
		🧊 Headless: true — не відкриває вікно браузера (для серверного виконання)
		"""
		if self._browser is None or not self._browser.is_connected():
			if self._playwright is None:
				self._playwright = await async_playwright().start()							            # 🧠 Запускаємо Playwright

			user_agent = self._config.get("playwright.user_agent")							            # 🧪 Кастомний user-agent
			logger.info(f"🚀 Запускаю браузер Chromium (Headless: {self._is_headless})...")

			self._browser = await self._playwright.chromium.launch(headless=self._is_headless)	        # 🌀 Запускаємо браузер
			self._context = await self._browser.new_context(user_agent=user_agent)						# 🧾 Створюємо контекст з user-agent
			logger.info("✅ Playwright-браузер ініціалізовано.")

	async def get_new_page(self) -> Page:
		"""
		📄 Створює нову сторінку (tab) у браузері з включеним stealth-режимом.
		🔸 Ініціалізує браузер при першому виклику
		🔸 Включає антибот-фікси через playwright_stealth
		"""
		await self._init_browser()
		if not self._context:
			raise RuntimeError("Контекст браузера не було створено.")

		page = await self._context.new_page()										# ➕ Створюємо вкладку
		await stealth_async(page)													# 🥷 Вмикаємо захист
		return page

	async def fetch_page_source(self, url: str) -> Optional[str]:
		"""
		🌐 Завантажує HTML-код сторінки із захистом від Cloudflare.

		🔁 Виконує до N спроб при виявленні CAPTCHA або захисту.
		🔐 Працює в headless-режимі з включеним stealth.
		🔎 Закриває вкладку після кожної спроби.
		"""
		page: Optional[Page] = None
		for attempt in range(1, self._retry_attempts + 1):									            # 🔁 Повторюємо запити до ліміту спроб
			try:
				page = await self.get_new_page()													    # 📥 Отримуємо нову вкладку з anti-bot
				logger.info(f"🌍 Завантаження (спроба {attempt}/{self._retry_attempts}): {url}")

				await page.goto(url, wait_until="networkidle", timeout=30000)			                # 📡 Завантажуємо сторінку
				await asyncio.sleep(1.5)																# ⏳ Додаємо затримку для рендеру DOM
				content = await page.content()													        # 📄 Отримуємо HTML-код
				
				# 🛑 Проверка на ошибку 502 или Cloudflare splash
				if "502 Bad Gateway" in content: 
					logger.error(f"❌ Сайт вернув 502 Bad Gateway! Повтор через {self._retry_delay_sec} сек...") 
					await asyncio.sleep(self._retry_delay_sec) 
					continue

				# 🛡️ Перевірка вмісту на фрази захисту Cloudflare
				if self._is_cloudflare_blocked(content):
					logger.warning(f"⚠️ Виявлено захист Cloudflare! Повтор через {self._retry_delay_sec} сек...")
					await asyncio.sleep(self._retry_delay_sec)									        # ⏱️ Чекаємо перед повтором
					continue

				logger.info("✅ Сторінка успішно завантажена.")
				return content

			except PlaywrightError as e:
				logger.error(f"❌ Помилка Playwright на спробі {attempt}: {e}")
				await asyncio.sleep(self._retry_delay_sec)										        # ⏳ Чекаємо перед повтором у разі помилки

			finally:
				if page and not page.is_closed():
					await page.close()																    # 🔒 Закриваємо вкладку після спроби

		logger.error(f"❌ Не вдалося завантажити сторінку після {self._retry_attempts} спроб.")
		return None

	async def close_browser(self):
		"""
		🔒 Закриває браузер і очищає ресурси.
		Викликається при завершенні роботи застосунку або для скидання стану.
		"""
		if self._browser:
			await self._browser.close()                          # 🚪 Коректно закриваємо браузер
			self._browser = None                                 # 🧹 Скидаємо shared екземпляр браузера
			self._context = None                                 # 🧹 Очищуємо контекст вкладок
			logger.info("🔒 Playwright-браузер закрито")
		if self._playwright:
			await self._playwright.stop()                        # ⛔ Зупиняємо runner
			self._playwright = None
			logger.info("🔌 Playwright-процес зупинено")
			
	def _is_cloudflare_blocked(self, html: str) -> bool:
		"""
		🛡️ Перевіряє, чи містить HTML фрази, що вказують на блокування Cloudflare.
		"""
		return any(phrase in html for phrase in self._cloudflare_phrases)
