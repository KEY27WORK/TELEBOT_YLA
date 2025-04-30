"""🧪 test_base_parser.py — unit-тести для BaseParser

Перевіряє:
- Витягування назви, ціни, опису, зображень
- Визначення ваги (з бази або GPT)
- Обробку кольорів/розмірів
"""

import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock
from core.parsing.base_parser import BaseParser

# 🔧 Тестовий підклас
class TestableParser(BaseParser):
    __test__ = False
    async def parse(self):
        return {}

@pytest.fixture
def parser_instance():
    parser = TestableParser("https://test.com")
    parser.soup = BeautifulSoup("""
        <html>
            <h1>Test Name</h1>
            <meta property="product:price:amount" content="25.5">
            <meta name="twitter:description" content="Test Description">
            <meta property="og:image" content="https://image.jpg">
            <div class="product-gallery__thumbnail-list">
                <button><img src="//cdn.test/1.jpg"/></button>
                <button><img src="https://cdn.test/2.jpg"/></button>
            </div>
            <div class="variant-picker__option">
                <label class="color-swatch"><span>Black</span></label>
                <label class="block-swatch"><span>Medium</span></label>
                <label class="block-swatch"><span>Large</span></label>
            </div>
        </html>
    """, "html.parser")
    return parser

@pytest.mark.asyncio
async def test_extract_title(parser_instance):
    assert await parser_instance.extract_title() == "Test Name"

@pytest.mark.asyncio
async def test_extract_price(parser_instance):
    assert await parser_instance.extract_price() == 25.5

@pytest.mark.asyncio
async def test_extract_description(parser_instance):
    assert await parser_instance.extract_description() == "Test Description"

@pytest.mark.asyncio
async def test_extract_image(parser_instance):
    assert await parser_instance.extract_image() == "https://image.jpg"

@pytest.mark.asyncio
async def test_extract_all_images(parser_instance):
    result = await parser_instance.extract_all_images()
    assert result == [
        "https://cdn.test/1.jpg",
        "https://cdn.test/2.jpg"
    ]

@pytest.mark.asyncio
async def test_extract_colors_sizes(parser_instance):
    result = await parser_instance.extract_colors_sizes()
    assert "Black" in result
    assert result["Black"] == ["M", "L"]

@patch("core.parsing.base_parser.ConfigService")
@patch("core.parsing.base_parser.TranslatorService")
@pytest.mark.asyncio
async def test_determine_weight_from_local(mock_translator, mock_config):
    mock_config.return_value.load_weight_data.return_value = {"tee": 0.75}
    parser = TestableParser("https://test.com")
    parser.config = mock_config.return_value
    parser.translator = mock_translator.return_value

    weight = await parser.determine_weight("tee", "desc", "img.jpg")
    assert weight == 0.75
    mock_translator.get_weight_estimate.assert_not_called()

@patch("core.parsing.base_parser.ConfigService")
@patch("core.parsing.base_parser.TranslatorService")
@pytest.mark.asyncio
async def test_determine_weight_from_gpt(mock_translator, mock_config):
    mock_config.return_value.load_weight_data.return_value = {}
    mock_translator.return_value.get_weight_estimate.return_value = 1.2

    parser = TestableParser("https://test.com")
    parser.config = mock_config.return_value
    parser.translator = mock_translator.return_value

    weight = await parser.determine_weight("hoodie", "desc", "img.jpg")
    assert weight == 1.2
    mock_translator.return_value.get_weight_estimate.assert_called_once()
    mock_config.return_value.update_weight_dict.assert_called_once()
