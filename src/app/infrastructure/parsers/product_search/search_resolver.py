# 🔍 search_resolver.py
"""
🔍 search_resolver.py — Асинхронний UI-пошук товару на сайті YoungLA через Playwright.

🔹 Переходить на головну сторінку
🔹 Імітує клік по кнопці пошуку (через JS)
🔹 Вводить запит у поле пошуку
🔹 Якщо є підказки — повертає перше посилання
🔹 Інакше сабмітить форму, чекає та парсить перший результат
🔹 Повертає URL товару або None
"""

# 🌐 Зовнішні бібліотеки
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError  # 🧪 Playwright для headless-пошуку

# 🔠 Системні імпорти
import logging  # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from app.domain.products.interfaces import IProductSearchProvider

# ================================
# 🏛️ КЛАС РЕЗОЛВЕРА ПОШУКУ
# ================================

logger = logging.getLogger(__name__)


class ProductSearchResolver(IProductSearchProvider):
    """
    🔍 Виконує пошук товару за запитом, імітуючи дії користувача на сайті.
    """

    BASE_URL = "https://www.youngla.com"  # 🌍 Базова адреса сайту YoungLA

    # 🧭 Селектори DOM-елементів, з якими працюємо
    SEARCH_ICON_SELECTOR = 'a[href="/search"]'  # 🔍 Кнопка/іконка відкриття пошуку
    SEARCH_INPUT_SELECTOR = 'input[type="search"]'  # 📝 Поле введення запиту
    PREDICTIVE_LINK_SELECTOR = 'predictive-search a[href*="/products/"]'  # ⚡ Підказки з дропдауна
    RESULT_LINK_SELECTOR = 'a[href*="/products/"]'  # 📄 Результати пошуку на сторінці
    SEARCH_FORM_SELECTOR = 'form.header-search__form'  # 📤 HTML-форма пошуку


    @classmethod
    async def resolve(cls, query: str) -> str | None:
        """
        📥 Пошук товару за назвою або артикулом.

        :param query: Наприклад: "W173 Nova Skirt"
        :return: URL товару або None
        """
        logger.info(f"🔍 Старт пошуку за запитом: {query}")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)  # Запускаємо Chromium у headless-режимі
                page = await browser.new_page()  # Створюємо нову сторінку

                # Виконуємо основні кроки UI-пошуку
                await cls._go_to_homepage(page)
                await cls._click_search_icon(page)
                await cls._fill_search_input(page, query)

                # Перевіряємо, чи є швидкі підказки
                result = await cls._check_predictive_suggestions(page)
                if result:
                    await browser.close()
                    return result

                # Якщо ні — сабмітимо форму пошуку і перевіряємо результат
                result = await cls._submit_search_form(page)
                await browser.close()
                return result

        except PlaywrightTimeoutError:
            logger.exception("❌ Таймаут при пошуку")
        except Exception as e:
            logger.exception(f"❌ Помилка пошуку: {e}")

        return None

    # ================================
    # 🔧 ДОПОМІЖНІ МЕТОДИ ДІЙ
    # ================================

    @classmethod
    async def _go_to_homepage(cls, page):
        """🌐 Переходить на головну сторінку сайту"""
        logger.info(f"🌐 Переходимо на головну: {cls.BASE_URL}")
        await page.goto(cls.BASE_URL, timeout=25000)

    @classmethod
    async def _click_search_icon(cls, page):
        """🖱️ Клікає по іконці пошуку (через JS для стабільності)"""
        try:
            await page.wait_for_selector(cls.SEARCH_ICON_SELECTOR, timeout=15000, state="attached")
            # Використовуємо evaluate для симуляції реального кліку через JS (безпечніше ніж click())
            await page.evaluate('selector => document.querySelector(selector)?.click()', cls.SEARCH_ICON_SELECTOR)
            logger.info("✅ Кнопка пошуку натиснута (через JS)")
        except PlaywrightTimeoutError:
            logger.exception("❌ Кнопка пошуку не знайдена")
            raise

    @classmethod
    async def _fill_search_input(cls, page, query: str):
        """⌨️ Вводить текстовий запит у поле пошуку"""
        try:
            await page.wait_for_selector(cls.SEARCH_INPUT_SELECTOR, timeout=5000)
            await page.fill(cls.SEARCH_INPUT_SELECTOR, query)
            logger.info(f"⌨️ Введено запит: {query}")
        except PlaywrightTimeoutError:
            logger.exception("❌ Поле пошуку не знайдено")
            raise

    @classmethod
    async def _check_predictive_suggestions(cls, page) -> str | None:
        """🔍 Перевіряє дропдаун з підказками і повертає перше посилання, якщо знайдено"""
        try:
            await page.wait_for_selector(cls.PREDICTIVE_LINK_SELECTOR, timeout=7000)
            el = await page.query_selector(cls.PREDICTIVE_LINK_SELECTOR)
            if el:
                href = await el.get_attribute("href")
                if href:
                    full_url = cls.BASE_URL + href if href.startswith("/") else href
                    logger.info(f"✅ Знайдено через підказки: {full_url}")
                    return full_url
        except PlaywrightTimeoutError:
            logger.warning("⚠️ Підказки не зʼявились — fallback на повну сторінку")
        return None

    @classmethod
    async def _submit_search_form(cls, page) -> str | None:
        """📤 Сабмітить форму пошуку і парсить перший результат зі сторінки результатів"""
        await page.locator(cls.SEARCH_FORM_SELECTOR).evaluate("form => form.submit()")
        await page.wait_for_load_state("networkidle", timeout=20000)

        # Перевірка на CAPTCHA (часто зустрічається в headless-режимі)
        html = await page.content()
        if "captcha" in html.lower():
            logger.error("🛑 CAPTCHA — headless режим заблоковано")
            return None

        try:
            # Чекаємо наявності хоча б одного результату товару на сторінці
            await page.wait_for_selector(cls.RESULT_LINK_SELECTOR, timeout=10000)

            # Вибираємо перше посилання з результатів
            result_el = await page.query_selector(cls.RESULT_LINK_SELECTOR)

            # Якщо знайдено елемент з посиланням
            if result_el:
                # Отримуємо значення атрибута href
                href = await result_el.get_attribute("href")

                # Перевіряємо, чи воно непорожнє
                if href:
                    # Додаємо базову адресу, якщо посилання починається з '/'
                    full_url = cls.BASE_URL + href if href.startswith("/") else href

                    # Логування успішного пошуку
                    logger.info(f"✅ Знайдено на сторінці результатів: {full_url}")

                    # Повертаємо повну URL-адресу товару
                    return full_url
        except PlaywrightTimeoutError:
            logger.warning("❌ Не знайдено жодного результату на сторінці")

        return None


## 🔎 app/infrastructure/parsers/product_search/search_resolver.py
#"""
#🔎 search_resolver.py — пошук товару на сайті YoungLA за текстовим запитом.
#
#🔹 Клас `ProductSearchResolver`:
#- Імітує поведінку користувача для пошуку товару.
#- Використовує спільний `WebDriverService` для роботи з браузером.
#- Реалізує логіку з фолбеком: спочатку швидкий пошук, потім повний.
#"""
#
## 🌐 Внешние библиотеки
#from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
#
## 🔠 Системные импорты
#import logging
#from typing import Optional
#
## 🧩 Внутренние модули проекта
#from app.infrastructure.web.webdriver_service import WebDriverService
#from app.domain.products.interfaces import IProductSearchProvider
#
## ================================
## 🏛️ КЛАС ПОШУКОВОГО РЕЗОЛВЕРА
## ================================
#class ProductSearchResolver(IProductSearchProvider):
#    """
#    🔍 Виконує пошук товару за запитом, імітуючи дії користувача на сайті.
#    """
#    BASE_URL = "https://www.youngla.com"
#    # ✅ ВИРІШЕННЯ: Додаємо селектор для всього діалогового вікна пошуку
#    SEARCH_DIALOG_SELECTOR = 'header-search'
#    SEARCH_INPUT_SELECTOR = 'input[type="search"]'
#    PREDICTIVE_LINK_SELECTOR = 'predictive-search a[href*="/products/"]'
#    RESULT_LINK_SELECTOR = 'a[href*="/products/"]'
#    SEARCH_FORM_SELECTOR = 'form.header-search__form'
#
#    def __init__(self, webdriver_service: WebDriverService):
#        """
#        ⚙️ Ініціалізація з впровадженням залежності WebDriverService.
#        """ 
#        self.webdriver_service = webdriver_service
#
#    # ================================
#    # 🔄 ГОЛОВНИЙ ПУБЛІЧНИЙ МЕТОД
#    # ================================
#    async def resolve(self, query: str) -> Optional[str]:
#        """
#        📥 Виконує повний цикл пошуку товару за назвою або артикулом.
#        """
#        logging.info(f"🔍 Виконуємо пошук за запитом: '{query}'")
#        page = None
#        try:
#            page = await self.webdriver_service.get_new_page()
#            
#            await self._perform_search_interaction(page, query)
#
#            predictive_url = await self._try_predictive_search(page)
#            if predictive_url:
#                logging.info(f"✅ Знайдено URL через швидкий пошук: {predictive_url}")
#                return predictive_url
#
#            logging.warning("⚠️ Підказки не з'явились, переходимо до повного пошуку.")
#            return await self._try_full_search(page)
#
#        except Exception as e:
#            logging.exception(f"❌ Критична помилка під час пошуку товару: {e}")
#            return None
#        finally:
#            if page and not page.is_closed():
#                await page.close()
#
#    # ================================
#    # 🕵️‍♂️ ПРИВАТНІ ДОПОМІЖНІ МЕТОДИ
#    # ================================
#    async def _perform_search_interaction(self, page: Page, query: str):
#        """
#        Виконує повну послідовність дій: переходить на сайт,
#        клікає на пошук і вводить запит, надійно чекаючи на кожен крок.
#        """
#        await page.goto(self.BASE_URL, timeout=25000)
#        logging.info(f"🌐 Перехід на головну сторінку: {self.BASE_URL}")
#
#        # Крок 1: Клікаємо на іконку пошуку, щоб викликати діалогове вікно
#        logging.info("⌛ Очікуємо та клікаємо на іконку пошуку...")
#        await page.get_by_role("link", name="Open search").click(timeout=15000)
#        logging.info("✅ Іконка пошуку знайдена та натиснута.")
#
#        # ✅ КРОК 2 (НАЙВАЖЛИВІШИЙ): Чекаємо, доки з'явиться ВСЕ ВІКНО ПОШУКУ.
#        # Це гарантує, що всі анімації завершилися.
#        search_dialog = page.locator(self.SEARCH_DIALOG_SELECTOR)
#        await search_dialog.wait_for(state="visible", timeout=15000)
#        logging.info("✅ Діалогове вікно пошуку стало видимим.")
#
#        # Крок 3: Тільки тепер, коли вікно гарантовано видиме,
#        # шукаємо поле вводу всередині нього і заповнюємо.
#        logging.info("⌛ Заповнюємо поле вводу...")
#        await search_dialog.locator(self.SEARCH_INPUT_SELECTOR).fill(query)
#        logging.info(f"⌨️ Введено запит у поле пошуку: '{query}'")
#
#    async def _try_predictive_search(self, page: Page) -> Optional[str]:
#        """
#        Спроба знайти посилання у випадаючому списку швидких результатів.
#        """
#        try:
#            await page.wait_for_selector(self.PREDICTIVE_LINK_SELECTOR, timeout=7000)
#            first_link_element = await page.query_selector(self.PREDICTIVE_LINK_SELECTOR)
#            if first_link_element:
#                href = await first_link_element.get_attribute("href")
#                if href:
#                    return self.BASE_URL + href if href.startswith("/") else href
#        except PlaywrightTimeoutError:
#            return None
#        return None
#
#    async def _try_full_search(self, page: Page) -> Optional[str]:
#        """
#        Виконує повний пошук, відправляючи форму та аналізуючи сторінку результатів.
#        """
#        await page.locator(self.SEARCH_FORM_SELECTOR).evaluate("form => form.submit()")
#        logging.info("📤 Форму пошуку відправлено.")
#
#        await page.wait_for_load_state("networkidle", timeout=20000)
#        
#        content = await page.content()
#        if "captcha" in content.lower():
#            logging.error("🛑 Виявлено CAPTCHA на сторінці. Пошук неможливий.")
#            return None
#
#        first_result = await page.query_selector(self.RESULT_LINK_SELECTOR)
#        if first_result:
#            href = await first_result.get_attribute("href")
#            if href:
#                full_url = self.BASE_URL + href if href.startswith("/") else href
#                logging.info(f"✅ Знайдено URL на сторінці результатів: {full_url}")
#                return full_url
#        
#        logging.warning("⚠️ Посилань на товари не знайдено на сторінці результатів.")
#        return None
#