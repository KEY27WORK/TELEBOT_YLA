""" 🧭 webdriver_service.py — керування браузером через Playwright для парсингу YoungLA.

🔹 Клас `WebDriverService`:
- Завантажує HTML-сторінки через асинхронний браузер
- Автоматично закриває браузер після завантаження
- Працює без блокувань і зависань
- Не потребує перезапусків драйвера

Використовує:
- playwright для асинхронного керування браузером
- logging для логування подій
"""

import logging
import asyncio
from playwright.async_api import async_playwright, Error as PlaywrightError
from playwright_stealth import stealth_async


class WebDriverService:
    """ 🧭 Сервіс завантаження сторінок через Playwright."""

    @staticmethod
    async def fetch_page_source(url: str) -> str | None:
        """ 🌐 Асинхронно завантажує HTML-код сторінки з обхідною обробкою захисту."""

        max_retries = 5

        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"🌍 Завантаження через Playwright (спроба {attempt}): {url}")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    )
                    page = await context.new_page()
                    await stealth_async(page)

                    await page.goto(url, timeout=30000)
                    await asyncio.sleep(1.5)  # Безпечна пауза

                    # Перевірка на Cloudflare або закриту сторінку
                    content = await page.content()
                    if "Your connection needs to be verified" in content or "Please complete the security check" in content:
                        logging.warning("⚠️ Виявлено захист Cloudflare! Повторна спроба...")
                        await browser.close()
                        continue

                    await browser.close()
                    logging.info("✅ Сторінка успішно завантажена через Playwright.")
                    return content

            except PlaywrightError as e:
                logging.error(f"❌ Помилка Playwright при завантаженні: {e}")
                await asyncio.sleep(1.5)  # Безпечна пауза

        logging.error("❌ Не вдалося обійти захист Cloudflare після 5 спроб.")
        return None