"""
🧪 test_universal_product_parser.py — unit-тести для UniversalProductParser

Перевіряє:
- Визначення валюти за URL
- Коректний виклик parse() з моками
- Обробку помилки для невідомого регіону
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.cores.parsers.products.universal_product_parser import UniversalProductParser


def test_detect_currency_us():
    parser = UniversalProductParser("https://youngla.com/products/abc123")
    assert parser.currency == "USD"


def test_detect_currency_eu():
    parser = UniversalProductParser("https://eu.youngla.com/products/abc123")
    assert parser.currency == "EUR"


def test_detect_currency_uk():
    parser = UniversalProductParser("https://uk.youngla.com/products/abc123")
    assert parser.currency == "GBP"


def test_detect_currency_invalid():
    with pytest.raises(ValueError):
        UniversalProductParser("https://unknown.youngla.shop/collections")


@patch("core.parsing.products.universal_product_parser.UniversalProductParser.fetch_page", new_callable=AsyncMock)
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.extract_title", new_callable=AsyncMock, return_value="Test Tee")
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.extract_description", new_callable=AsyncMock, return_value="Comfortable tee")
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.extract_image", new_callable=AsyncMock, return_value="https://image.jpg")
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.extract_colors_sizes", new_callable=AsyncMock, return_value="Red / M, L")
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.determine_weight", new_callable=AsyncMock, return_value=0.5)
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.extract_all_images", new_callable=AsyncMock, return_value=["img1.jpg", "img2.jpg"])
@patch("core.parsing.products.universal_product_parser.UniversalProductParser.extract_price", new_callable=AsyncMock, return_value=29.99)
@pytest.mark.asyncio
async def test_parse_success(
    mock_price, mock_imgs, mock_weight, mock_colors, mock_image,
    mock_desc, mock_title, mock_fetch
):
    mock_fetch.return_value = True

    parser = UniversalProductParser("https://youngla.com/products/tee")
    result = await parser.parse()

    assert result["title"] == "Test Tee"
    assert result["price"] == 29.99
    assert result["currency"] == "USD"
    assert result["description"] == "Comfortable tee"
    assert result["main_image"] == "https://image.jpg"
    assert result["colors_sizes"] == "Red / M, L"
    assert result["images"] == ["img1.jpg", "img2.jpg"]
    assert result["weight"] == 0.5


@patch("core.parsing.products.universal_product_parser.UniversalProductParser.fetch_page", new_callable=AsyncMock, return_value=False)
@pytest.mark.asyncio
async def test_parse_failed_fetch(mock_fetch):
    parser = UniversalProductParser("https://youngla.com/products/fail")
    result = await parser.parse()
    assert result == {}
