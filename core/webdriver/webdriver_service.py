''' 🧭 webdriver_service.py — керування браузером через Playwright для парсингу YoungLA.

🔹 Клас `WebDriverService`:
- Працює через один Playwright-браузер (shared singleton)
- Переюзує контекст, сторінку і браузер
- Працює стабільно з Cloudflare

Використовує:
- playwright.async_api для браузера
- playwright_stealth для обходу захисту
- logging для логування
'''

# 📦 Стандартні
import logging
import asyncio
from typing import Optional

# 🌐 Playwright + Stealth
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
from playwright_stealth import stealth_async


class WebDriverService:
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None

    @classmethod
    async def _init_browser(cls):
        if cls._browser is None:
            playwright = await async_playwright().start()
            cls._browser = await playwright.chromium.launch(headless=True)
            cls._context = await cls._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            cls._page = await cls._context.new_page()
            await stealth_async(cls._page)
            logging.info("🚀 Playwright-браузер ініціалізовано (shared instance)")

    @classmethod
    async def fetch_page_source(cls, url: str) -> Optional[str]:
        """🌐 Завантажує HTML через загальний браузер.
        Повторює до 5 разів при Cloudflare.
        """
        await cls._init_browser()
    
        for attempt in range(1, 6):
            try:
                logging.info(f"🌍 Завантаження через Playwright (спроба {attempt}): {url}")
                page = await cls._context.new_page()
                await stealth_async(page)
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1.5)
                content = await page.content()
                await page.close()

                if "Your connection needs to be verified" in content or "Please complete the security check" in content:
                    logging.warning("⚠️ Виявлено захист Cloudflare! Повторна спроба...")
                    continue
                
                logging.info("✅ Сторінка успішно завантажена через Playwright.")
                return content
    
            except PlaywrightError as e:
                logging.error(f"❌ Помилка Playwright при завантаженні: {e}")
                await asyncio.sleep(2)
    
        logging.error("❌ Не вдалося обійти захист Cloudflare після 5 спроб.")
        return None
    

    @classmethod
    async def close_browser(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            cls._context = None
            cls._page = None
            logging.info("🔒 Playwright-браузер закрито")
