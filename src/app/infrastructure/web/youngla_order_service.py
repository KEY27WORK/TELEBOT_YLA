# 🛒 src/app/infrastructure/web/youngla_order_service.py
"""
🛒 YoungLAOrderService — авто-додавання товарів у кошик YoungLA.

🔹 Парсить .txt-файли зі SKU/Color/Size (метод `parse_youngla_order_file`).
🔹 Playwright відкриває сторінки й обирає варіанти.
🔹 Натискає Add to cart і переходить на Protected Checkout.
🔹 Завершує сценарій з відкритою вкладкою браузера.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from playwright.async_api import (  # type: ignore[attr-defined] (Playwright типи)
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Locator,
    Page,
    Playwright,
    async_playwright,
)

# 🔠 Системні імпорти
import asyncio
import logging
import re
from typing import Any, Callable, Dict, Iterable, List

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService
from app.shared.utils.logger import LOG_NAME
from .youngla_order_parser import YoungLAOrderProduct, parse_youngla_order_file


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.youngla_order")


# ================================
# 🛒 ОСНОВНИЙ СЕРВІС
# ================================
class YoungLAOrderService:
    """🧠 Сервіс авто-додавання товарів у кошик."""

    BASE_URL = "https://www.youngla.com"

    def __init__(self, config_service: ConfigService) -> None:
        self._config = config_service
        cfg = config_service.get("orders.youngla", {}) or {}
        self._headless = bool(cfg.get("headless", False))
        self._keep_browser_open = bool(cfg.get("keep_browser_open", True))
        self._delay_between_adds = self._as_float(cfg.get("add_delay_sec"), default=1.0)
        self._color_delay = self._as_float(cfg.get("color_delay_sec"), default=0.5)
        self._size_delay = self._as_float(cfg.get("size_delay_sec"), default=0.5)
        self._product_delay = self._as_float(cfg.get("product_delay_sec"), default=2.0)
        self._page_ready_delay = self._as_float(cfg.get("page_ready_delay_sec"), default=1.0)
        self._checkout_delay = self._as_float(cfg.get("checkout_delay_sec"), default=1.0)
        self._slow_mo_ms = self._as_float(cfg.get("slow_mo_ms"), default=0.0)
        self._devtools_enabled = bool(cfg.get("devtools", False))
        self._launch_channel = cfg.get("launch_channel") or config_service.get(
            "playwright.launch_channel"
        )
        self._navigation_timeout_ms = self._as_float(
            cfg.get("navigation_timeout_ms")
            or config_service.get("playwright.navigation_timeout_ms"),
            default=30000,
        )

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ================================
    # 🧮 ПУБЛІЧНИЙ API
    # ================================
    async def process_order_file(self, file_text: str) -> bool:
        """Опрацьовує файл замовлення за допомогою Playwright."""

        Args:
            file_text: Вміст .txt-файлу замовлень.

        Returns:
            bool: True, якщо хоча б один товар опрацьовано
                та відкрито checkout.
        """

        products = parse_youngla_order_file(file_text)
        if not products:
            logger.warning(
                "⚠️ Не вдалося розпізнати файл замовлень",
            )
            return False

        logger.info(
            "🤖 Стартую автоматизацію — знайдено %d SKU",
            len(products),
        )
        await self._close_previous_session()

        playwright: Playwright | None = None
        browser: Browser | None = None
        context: BrowserContext | None = None
        page: Page | None = None
        success = False

        try:
            playwright = await async_playwright().start()
            browser = await self._launch_browser(playwright)
            context = await browser.new_context()
            context.set_default_navigation_timeout(self._navigation_timeout_ms)
            context.set_default_timeout(self._navigation_timeout_ms)
            page = await context.new_page()

            success = await self._process_products(page, products)
            if success:
                await self._open_checkout(page)
                logger.info(
                    "✅ Checkout відкрито — браузер не закриваємо.",
                )
            return success
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "❌ Помилка при автоматизації YoungLA: %s",
                exc,
            )
            return False
        finally:
            if not success or not self._keep_browser_open:
                await self._safe_close(context, browser, playwright)
            else:
                self._playwright = playwright
                self._browser = browser
                self._context = context
                self._page = page

    # ================================
    # ⚙️ НИЗЬКОРІВНЕВІ ОПЕРАЦІЇ
    # ================================
    async def _process_products(
        self,
        page: Page,
        products: List[YoungLAOrderProduct],
    ) -> bool:
        processed = False
        for product in products:
            logger.info("📦 Обробка SKU %s (%s)", product.sku, product.name)
            try:
                opened = await self._open_product_page(page, product)
            except PlaywrightError as err:
                logger.error(
                    "❌ Не вдалося відкрити SKU %s: %s",
                    product.sku,
                    err,
                )
                continue

            if not opened:
                logger.warning("⚠️ SKU %s не знайдено на сайті", product.sku)
                continue

            await asyncio.sleep(self._page_ready_delay)
            for color, sizes in product.variants.items():
                color_selected = await self._select_color(page, product, color)
                if not color_selected:
                    continue

                await asyncio.sleep(self._color_delay)
                for size, qty in sizes.items():
                    await self._handle_size_variant(page, product, color, size, qty)
                    await asyncio.sleep(self._size_delay)

            processed = True
            await asyncio.sleep(self._product_delay)

        return processed

    async def _handle_size_variant(
        self,
        page: Page,
        product: YoungLAOrderProduct,
        color: str,
        size: str,
        qty: int,
    ) -> None:
        size_selected = await self._select_size(page, product, size)
        if not size_selected:
            return

        await asyncio.sleep(self._size_delay)
        await self._add_to_cart(page, product, color, size, qty)

    async def _open_product_page(self, page: Page, product: YoungLAOrderProduct) -> bool:
        product_url = f"{self.BASE_URL}/products/{product.sku}"
        logger.info("🔗 Відкриваю %s", product_url)
        response = await page.goto(product_url)
        if response and response.status == 200:
            await page.wait_for_load_state("domcontentloaded")
            return True

        logger.info(
            "🔍 SKU %s не знайдено прямим URL → пошук",
            product.sku,
        )
        return await self._open_product_via_search(page, product)

    async def _open_product_via_search(self, page: Page, product: YoungLAOrderProduct) -> bool:
        search_url = f"{self.BASE_URL}/search?q={product.sku}"
        await page.goto(search_url)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(self._page_ready_delay)

        locators = [
            page.get_by_role("link", name=re.compile(product.sku, re.IGNORECASE)),
            page.get_by_text(product.name, exact=False),
        ]
        for locator in locators:
            try:
                await locator.first.click()
                await page.wait_for_load_state("domcontentloaded")
                return True
            except PlaywrightError:
                continue
        return False

    async def _select_color(
        self,
        page: Page,
        product: YoungLAOrderProduct,
        color: str,
    ) -> bool:
        pattern = re.compile(re.escape(color), re.IGNORECASE)
        candidates = [
            page.get_by_role("button", name=pattern),
            page.get_by_role("radio", name=pattern),
            page.get_by_text(color, exact=False),
        ]
        for locator in candidates:
            try:
                if await locator.count() == 0:
                    continue
                await locator.first.click()
                logger.info("🎨 Обрано колір %s для SKU %s", color, product.sku)
                return True
            except PlaywrightError:
                continue
        logger.error("❌ Колір %s не знайдено (SKU %s)", color, product.sku)
        return False

    async def _select_size(
        self,
        page: Page,
        product: YoungLAOrderProduct,
        size: str,
    ) -> bool:
        pattern = re.compile(rf"^{re.escape(size)}$", re.IGNORECASE)
        candidates = [
            page.get_by_role("button", name=pattern),
            page.get_by_text(size, exact=True),
        ]
        for locator in candidates:
            try:
                if await locator.count() == 0:
                    continue
                button = locator.first
                if await button.is_disabled():
                    logger.warning(
                        "⚠️ Розмір %s (%s) відсутній у наявності",
                        size,
                        product.sku,
                    )
                    return False
                await button.click()
                logger.info("📐 Обрано розмір %s (%s)", size, product.sku)
                return True
            except PlaywrightError:
                continue
        logger.error("❌ Розмір %s не знайдено (SKU %s)", size, product.sku)
        return False

    async def _add_to_cart(
        self,
        page: Page,
        product: YoungLAOrderProduct,
        color: str,
        size: str,
        qty: int,
    ) -> None:
        button = page.get_by_role("button", name=re.compile("add to cart", re.IGNORECASE))
        for idx in range(qty):
            try:
                await button.first.click()
                logger.info(
                    "✅ Додано %s / %s / %s (%d/%d)",
                    product.sku,
                    color,
                    size,
                    idx + 1,
                    qty,
                )
            except PlaywrightError as err:
                logger.error(
                    "❌ Помилка при додаванні %s (%s %s): %s",
                    product.sku,
                    color,
                    size,
                    err,
                )
                break

            await asyncio.sleep(self._delay_between_adds)
            await self._close_cart_drawer(page)

    async def _close_cart_drawer(self, page: Page) -> None:
        candidates: Iterable[Callable[[Page], Locator]] = (
            lambda p: p.get_by_role("button", name=re.compile("close", re.IGNORECASE)),
            lambda p: p.get_by_role("button", name=re.compile("continue shopping", re.IGNORECASE)),
        )
        for factory in candidates:
            try:
                locator = factory(page)
                if await locator.count() == 0:
                    continue
                button = locator.first
                if await button.is_visible():
                    await button.click()
                    await asyncio.sleep(0.2)
                    return
            except PlaywrightError:
                continue

    async def _open_checkout(self, page: Page) -> None:
        await page.goto(f"{self.BASE_URL}/cart")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(self._checkout_delay)
        checkout_locators = [
            page.get_by_text("Protected Checkout", exact=False),
            page.get_by_role("link", name=re.compile("checkout", re.IGNORECASE)),
            page.get_by_role("button", name=re.compile("checkout", re.IGNORECASE)),
        ]
        for locator in checkout_locators:
            try:
                if await locator.count() == 0:
                    continue
                await locator.first.click()
                return
            except PlaywrightError:
                continue
        logger.warning(
            "⚠️ Кнопку Checkout не знайдено (кошик відкрито)",
        )

    async def _launch_browser(self, playwright: Playwright) -> Browser:
        kwargs: Dict[str, Any] = {"headless": self._headless}
        if self._launch_channel:
            kwargs["channel"] = self._launch_channel
        if self._devtools_enabled:
            kwargs["devtools"] = True
        if self._slow_mo_ms:
            kwargs["slow_mo"] = self._slow_mo_ms
        return await playwright.chromium.launch(**kwargs)

    async def _close_previous_session(self) -> None:
        if not self._browser:
            return
        await self._safe_close(self._context, self._browser, self._playwright)
        self._browser = None
        self._context = None
        self._playwright = None
        self._page = None

    async def _safe_close(
        self,
        context: BrowserContext | None,
        browser: Browser | None,
        playwright: Playwright | None,
    ) -> None:
        try:
            if context:
                await context.close()
        except Exception:  # noqa: BLE001
            logger.debug(
                "⚠️ Не вдалося закрити контекст",
                exc_info=True,
            )
        try:
            if browser:
                await browser.close()
        except Exception:  # noqa: BLE001
            logger.debug(
                "⚠️ Не вдалося закрити браузер",
                exc_info=True,
            )
        try:
            if playwright:
                await playwright.stop()
        except Exception:  # noqa: BLE001
            logger.debug(
                "⚠️ Не вдалося зупинити Playwright",
                exc_info=True,
            )

    @staticmethod
    def _as_float(value: Any, *, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default


__all__ = ["YoungLAOrderService"]
