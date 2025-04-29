"""
🧪 test_webdriver_service.py — unit-тест для WebDriverService на Playwright

Перевіряє:
- Завантаження сторінки через fetch_page_source
"""

import pytest
from core.webdriver.webdriver_service import WebDriverService

pytestmark = pytest.mark.asyncio


async def test_fetch_page_source_success(monkeypatch):
    async def mock_fetch_page_source(url):
        return "<html><body>Hello</body></html>"

    monkeypatch.setattr(WebDriverService, "fetch_page_source", mock_fetch_page_source)

    content = await WebDriverService.fetch_page_source("https://example.com")
    assert "<body>Hello</body>" in content


async def test_fetch_page_source_fail(monkeypatch):
    async def mock_fetch_page_source(url):
        return None

    monkeypatch.setattr(WebDriverService, "fetch_page_source", mock_fetch_page_source)

    content = await WebDriverService.fetch_page_source("https://fail.com")
    assert content is None
