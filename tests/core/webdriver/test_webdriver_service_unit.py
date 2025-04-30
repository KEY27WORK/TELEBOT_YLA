'''🧪 test_webdriver_service.py — unit-тести для WebDriverService

Перевіряє:
- Успішне завантаження HTML через fetch_page_source
- Обробку Cloudflare-захисту (мок)
'''

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.webdriver.webdriver_service import WebDriverService

pytestmark = pytest.mark.asyncio


@patch("core.webdriver.webdriver_service.async_playwright", new_callable=AsyncMock)
@patch("core.webdriver.webdriver_service.stealth_async", new_callable=AsyncMock)
async def test_fetch_page_source_success(mock_stealth, mock_playwright):
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_page.goto.return_value = None
    mock_page.content.return_value = "<html><body>Hello</body></html>"

    WebDriverService._browser = None
    WebDriverService._context = None
    WebDriverService._page = None

    # 🧩 Вручну викликаємо ініціалізацію браузера з підставленим mock
    async def _init_browser_mock():
        WebDriverService._browser = mock_browser
        WebDriverService._context = mock_context
        WebDriverService._page = mock_page
    WebDriverService._init_browser = classmethod(lambda cls: _init_browser_mock())

    result = await WebDriverService.fetch_page_source("https://test.com")
    assert "Hello" in result


@patch("core.webdriver.webdriver_service.async_playwright", new_callable=AsyncMock)
@patch("core.webdriver.webdriver_service.stealth_async", new_callable=AsyncMock)
async def test_fetch_page_source_cloudflare(mock_stealth, mock_playwright):
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    # Cloudflare контент (буде повторна спроба)
    mock_page.goto.return_value = None
    mock_page.content.return_value = "Your connection needs to be verified"

    WebDriverService._browser = None
    WebDriverService._context = None
    WebDriverService._page = None

    async def _init_browser_mock():
        WebDriverService._browser = mock_browser
        WebDriverService._context = mock_context
        WebDriverService._page = mock_page
    WebDriverService._init_browser = classmethod(lambda cls: _init_browser_mock())

    result = await WebDriverService.fetch_page_source("https://cf.com")
    assert result is None
