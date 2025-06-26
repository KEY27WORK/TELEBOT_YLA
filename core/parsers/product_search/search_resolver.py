# 📁 core/parsers/product_search/search_resolver.py

"""🔍 search_resolver.py — знаходить URL першого товару по назві чи артикулу через UI пошуку."""

# 🧱 Системні
import urllib.parse
import logging

# 🧰 Інструменти автоматизації
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class ProductSearchResolver:
    """
    🔍 Пошуковий резолвер: знаходить перший товар на сайті YoungLA по назві або артикулу.
    """

    BASE_URL = "https://www.youngla.com"

    @classmethod
    async def resolve(cls, query: str) -> str | None:
        """
        Приймає текстовий запит (назва або артикул), повертає повну URL-адресу першого товару.

        :param query: Назва або артикул товару (наприклад, "W173 Nova Skirt")
        :return: Повна URL-адреса першого знайденого товару або None
        """
        logger.info(f"🔍 Виконуємо пошук за запитом: {query}")

        try:
            async with async_playwright() as p:
                logger.info("🚀 Запускаємо браузер Playwright...")
                browser = await p.chromium.launch(headless=False, slow_mo=200, devtools=True)
                page = await browser.new_page()

                logger.info(f"🌐 Переходимо на головну сторінку: {cls.BASE_URL}")
                await page.goto(cls.BASE_URL, timeout=25000)
                await page.screenshot(path="step1_home.png")

                logger.info("📃 Контент після відкриття головної сторінки:")
                content_main = await page.content()
                logger.info(content_main[:3000])
                with open("page_home.html", "w", encoding="utf-8") as f:
                    f.write(content_main)

                logger.info("⌛ Очікуємо появу кнопки пошуку...")
                try:
                    await page.wait_for_selector('a[href="/search"]', timeout=15000, state="attached")
                    logger.info("✅ Кнопка пошуку знайдена — клікаємо...")
                    await page.evaluate('document.querySelector("a[href=\\\"/search\\\"]")?.click()')
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Кнопка пошуку не зʼявилась. Частина HTML:")
                    logger.info(html[:3000])
                    raise

                await page.screenshot(path="step2_clicked_search.png")

                logger.info("⌛ Очікуємо поле для введення запиту...")
                try:
                    await page.wait_for_selector('input[type="search"]', timeout=5000)
                    logger.info("✅ Поле пошуку знайдено")
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Поле для пошуку не зʼявилось. Частина HTML:")
                    logger.info(html[:3000])
                    raise

                logger.info(f"⌨️ Вводимо запит у поле пошуку: {query}")
                await page.fill('input[type="search"]', query)

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

                logger.info("📤 Відправляємо форму пошуку вручну")
                await page.locator('form.header-search__form').evaluate("form => form.submit()")
                await page.screenshot(path="step3_search_filled.png")

                logger.info("⏳ Очікуємо завантаження результатів (networkidle + selector)...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                    logger.info("✅ Завантаження завершено")
                except PlaywrightTimeoutError:
                    html = await page.content()
                    logger.error("❌ Завантаження не завершено. Частина HTML:")
                    logger.info(html[:3000])
                    raise

                logger.info("🧪 Перевірка на наявність CAPTCHA або редиректів...")
                content = await page.content()
                if "captcha" in content.lower():
                    logger.error("🛑 Виявлено CAPTCHA на сторінці. Пошук неможливий у headless режимі.")
                    await page.screenshot(path="step4_captcha_detected.png")
                    await browser.close()
                    return None

                logger.debug("📃 Контент після пошуку:")
                logger.debug(content[:3000])

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
