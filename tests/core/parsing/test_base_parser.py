"""
🧪 test_base_parser.py — unit-тести для BaseParser

Перевіряє:
- Витягування назви, ціни, опису, зображень
- Визначення ваги (з локальної бази або GPT)
- Обробку кольорів/розмірів та форматування
"""

import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock
from core.parsing.base_parser import BaseParser

# 🔧 Тестовий клас для реалізації абстрактного
class TestableParser(BaseParser):
    __test__ = False
    async def parse(self):
        return {}

@pytest.fixture
def parser_instance():
    parser = TestableParser("https://test.com", currency_service=None)
    parser.soup = BeautifulSoup("""
        <html>
            <h1>Product Name</h1>
            <meta property="product:price:amount" content="24.99">
            <meta name="twitter:description" content="This is a description">
            <meta property="og:image" content="https://img.jpg">
            <div class="product-gallery__thumbnail-list">
                <button><img src="//cdn.img/1.jpg"/></button>
                <button><img src="https://cdn.img/2.jpg"/></button>
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
    result = await parser_instance.extract_title()
    assert result == "Product Name"

@pytest.mark.asyncio
async def test_extract_price(parser_instance):
    result = await parser_instance.extract_price()
    assert result == 24.99

@pytest.mark.asyncio
async def test_extract_description(parser_instance):
    result = await parser_instance.extract_description()
    assert result == "This is a description"

@pytest.mark.asyncio
async def test_extract_image(parser_instance):
    result = await parser_instance.extract_image()
    assert result == "https://img.jpg"

@pytest.mark.asyncio
async def test_extract_all_images(parser_instance):
    result = await parser_instance.extract_all_images()
    assert result == [
        "https://cdn.img/1.jpg",
        "https://cdn.img/2.jpg"
    ]

@pytest.mark.asyncio
async def test_extract_colors_sizes(parser_instance):
    result = await parser_instance.extract_colors_sizes()
    assert "Black: M, L" in result or "Black: Medium, Large" in result


@patch("core.parsing.base_parser.ConfigService")
@patch("core.parsing.base_parser.TranslatorService")
@pytest.mark.asyncio
async def test_determine_weight_from_base(mock_translator, mock_config):
    mock_config.return_value.load_weight_data.return_value = {"tee": 0.6}
    parser = TestableParser("url", currency_service=None)
    parser.config = mock_config.return_value
    parser.translator = mock_translator.return_value

    result = await parser.determine_weight("Tee", "desc", "image.jpg")
    assert result == 0.6
    mock_translator.get_weight_estimate.assert_not_called()


@patch("core.parsing.base_parser.ConfigService")
@patch("core.parsing.base_parser.TranslatorService")
@pytest.mark.asyncio
async def test_determine_weight_via_gpt(mock_translator, mock_config):
    mock_config.return_value.load_weight_data.return_value = {}
    mock_translator.return_value.get_weight_estimate.return_value = 1.2

    parser = TestableParser("url", currency_service=None)
    parser.config = mock_config.return_value
    parser.translator = mock_translator.return_value

    result = await parser.determine_weight("Tee", "desc", "image.jpg")
    assert result == 1.2
    mock_config.return_value.update_weight_dict.assert_called_once()
    mock_translator.return_value.get_weight_estimate.assert_called_once()
