"""
🔍 ProductSearchResolver — асинхронний резолвер, що використовує Playwright для UI-пошуку товару на сайті YoungLA.

🔧 Поведінка:
- Відкриває головну сторінку сайту
- Імітує клік по кнопці пошуку, вводить запит
- Якщо зʼявляється дропдаун із підказками — повертає перше посилання
- Якщо ні — сабмітить форму, парсить сторінку результатів
- Повертає URL першого товару або None, якщо нічого не знайдено

💡 Працює у headless-режимі — готово до продакшену
"""

# 🧱 Системні
import logging  # 📋 Логування процесу

# 🧰 Інструменти автоматизації
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError  # 🧪 Асинхронна автоматизація браузера

# 🔧 Налаштування логера
logger = logging.getLogger(__name__)


class ProductSearchResolver:
    """
    🔍 ProductSearchResolver — асинхронний резолвер, що виконує пошук товару за запитом через інтерфейс сайту YoungLA.

    ✅ Алгоритм дій:
    - відкриває головну сторінку
    - відкриває вікно пошуку, вводить запит
    - перевіряє наявність підказок у дропдауні
    - якщо є — бере перше посилання
    - якщо ні — сабмітить форму, чекає на повну сторінку результатів
    - парсить посилання першого товару

    ⚠️ Якщо зустрічає CAPTCHA — повертає None
    """

    BASE_URL = "https://www.youngla.com"  # 🌐 Базова URL-адреса магазину

    @classmethod
    async def resolve(cls, query: str) -> str | None:
        """
        📥 Пошук товару за назвою або артикулом. Повертає URL першого знайденого товару.

        :param query: Назва або артикул (наприклад, "W173 Nova Skirt")
        :return: URL або None, якщо не знайдено
        """
        logger.info(f"🔍 Виконуємо пошук за запитом: {query}")

        try:
            async with async_playwright() as p:
                logger.info("🚀 Запускаємо браузер Playwright...")
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                logger.info(f"🌐 Переходимо на головну сторінку: {cls.BASE_URL}")
                await page.goto(cls.BASE_URL, timeout=25000)

                # 🔍 Клік по кнопці пошуку
                logger.info("⌛ Очікуємо появу кнопки пошуку...")
                try:
                    await page.wait_for_selector('a[href="/search"]', timeout=15000, state="attached")
                    logger.info("✅ Кнопка пошуку знайдена — клікаємо...")
                    await page.evaluate('document.querySelector("a[href=\\\"/search\\\"]")?.click()')
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Кнопка пошуку не зʼявилась. Частина HTML:")
                    logger.debug(html[:3000])
                    raise

                # ⌨️ Введення запиту у поле
                logger.info("⌛ Очікуємо поле для введення запиту...")
                try:
                    await page.wait_for_selector('input[type="search"]', timeout=5000)
                    logger.info("✅ Поле пошуку знайдено")
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Поле для пошуку не зʼявилось. Частина HTML:")
                    logger.debug(html[:3000])
                    raise

                logger.info(f"⌨️ Вводимо запит у поле пошуку: {query}")
                await page.fill('input[type="search"]', query)

                # 📩 Пробуємо зчитати дропдаун з підказками
                logger.info("⏳ Чекаємо на появу дропдауну з результатами...")
                try:
                    await page.wait_for_selector('predictive-search a[href*="/products/"]', timeout=7000)
                    logger.info("✅ Є підказки — пробуємо витягнути перший товар")

                    first_predictive_link = await page.query_selector('predictive-search a[href*="/products/"]')
                    if first_predictive_link:
                        href = await first_predictive_link.get_attribute("href")
                        logger.info(f"🔗 Знайдено посилання в підказках: {href}")
                        if href:
                            full_url = cls.BASE_URL + href if href.startswith("/") else href
                            logger.info(f"✅ Повертаємо: {full_url}")
                            await browser.close()
                            return full_url
                except PlaywrightTimeoutError:
                    logger.warning("⚠️ Підказки не зʼявились — fallback на повну сторінку")

                # 📤 Фолбек: сабмітимо форму вручну
                logger.info("📤 Відправляємо форму пошуку вручну")
                await page.locator('form.header-search__form').evaluate("form => form.submit()")

                logger.info("⏳ Очікуємо завантаження результатів (networkidle + selector)...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                    logger.info("✅ Завантаження завершено")
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Завантаження не завершено. Частина HTML:")
                    logger.info(html[:3000])
                    raise

                # 🔒 Перевірка на CAPTCHA
                logger.info("🧪 Перевірка на наявність CAPTCHA або редиректів...")
                content = await page.content()
                if "captcha" in content.lower():
                    logger.error("🛑 Виявлено CAPTCHA на сторінці. Пошук неможливий у headless режимі.")
                    await browser.close()
                    return None

                # 🔗 Пошук першого товару
                logger.info("🔗 Шукаємо перше посилання на товар...")
                try:
                    await page.wait_for_selector('a[href*="/products/"]', timeout=10000)
                    logger.info("✅ Посилання знайдене")
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Посилання на товари не знайдено. Частина HTML:")
                    logger.debug(html[:3000])
                    raise

                first_result = await page.query_selector('a[href*="/products/"]')

                if first_result:
                    href = await first_result.get_attribute("href")
                    logger.info(f"🔗 Знайдено посилання: {href}")
                    if href:
                        full_url = cls.BASE_URL + href if href.startswith("/") else href
                        logger.info(f"✅ Повна URL-адреса товару: {full_url}")
                        await browser.close()
                        return full_url

                logger.warning("⚠️ Посилань на товари не знайдено на сторінці результатів.")
                await browser.close()
                return None

        except PlaywrightTimeoutError:
            logger.error("❌ Таймаут: сторінка або результати не завантажились вчасно.")
        except Exception as e:
            logger.exception(f"❌ Помилка пошуку товару: {e}")

        return None