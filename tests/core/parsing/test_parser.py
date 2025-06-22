"""
🧪 test_parser.py — тести для ProductParser та CollectionParser.

Перевіряє:
- Парсинг товару (успіх та помилка)
- Отримання посилань із колекції
"""

import pytest
from unittest.mock import patch, AsyncMock
from core.parsers.parser import ProductParser, CollectionParser


@pytest.mark.asyncio
async def test_product_parser_success():
    url = "https://www.youngla.com/products/test-product"

    mock_data = {
        "title": "Test Product",
        "price": "99.99",
        "currency": "USD",
        "description": "Test Description",
        "main_image": "https://image.jpg",
        "colors_sizes": "Black: S, M, L",
        "images": ["https://image1.jpg", "https://image2.jpg"],
        "weight": "0.8"
    }

    with patch("core.parsing.parser.UniversalProductParser.parse", new_callable=AsyncMock, return_value=mock_data):
        parser = ProductParser(url)
        result = await parser.get_product_info()

        assert result[0] == "Test Product"
        assert result[1] == 99.99
        assert result[4] == 0.8
        assert result[7] == "USD"


@pytest.mark.asyncio
async def test_product_parser_parse_exception():
    url = "https://www.youngla.com/products/error-product"

    with patch("core.parsing.parser.UniversalProductParser.parse", new_callable=AsyncMock, side_effect=Exception("fail")):
        parser = ProductParser(url)
        result = await parser.get_product_info()

        assert result == ("Помилка", 0.0, "Помилка", "", 0.5, "", [], "USD")


@pytest.mark.asyncio
async def test_collection_parser_extract_links():
    url = "https://www.youngla.com/collections/test-collection"
    mock_links = [
        "https://youngla.com/products/item1",
        "https://youngla.com/products/item2"
    ]

    with patch("core.parsing.parser.UniversalCollectionParser.extract_product_links", new_callable=AsyncMock, return_value=mock_links):
        parser = CollectionParser(url)
        result = await parser.extract_product_links()

        assert result == mock_links
