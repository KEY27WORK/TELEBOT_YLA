'''🧪 test_availability_checker.py — unit-тест для перевірки наявності в регіонах

Перевіряє:
- check_availability_across_regions
- _check_region_availability (через мок)
'''

import pytest
from unittest.mock import patch, AsyncMock
from app.cores.parsers import availability_checker

pytestmark = pytest.mark.asyncio


@patch("core.parsing.availability_checker.BaseParser")
async def test_check_availability_across_regions_all_available(mock_parser_cls):
    mock_parser = AsyncMock()
    mock_parser.is_product_available.return_value = True
    mock_parser_cls.side_effect = lambda url: mock_parser

    result = await availability_checker.check_availability_across_regions("/products/test")

    assert "🇺🇸 - ✅" in result
    assert "🇪🇺 - ✅" in result
    assert "🇬🇧 - ✅" in result


@patch("core.parsing.availability_checker.BaseParser")
async def test_check_availability_across_regions_mixed(mock_parser_cls):
    def parser_mock_gen(url):
        mock = AsyncMock()
        if "eu" in url:
            mock.is_product_available.return_value = False
        else:
            mock.is_product_available.return_value = True
        return mock

    mock_parser_cls.side_effect = parser_mock_gen
    result = await availability_checker.check_availability_across_regions("/products/test")

    assert "🇺🇸 - ✅" in result
    assert "🇪🇺 - ❌" in result
    assert "🇬🇧 - ✅" in result


@patch("core.parsing.availability_checker.BaseParser")
async def test_check_availability_across_regions_error(mock_parser_cls):
    async def parser_error(url):
        raise Exception("fail")

    mock_parser_cls.side_effect = parser_error
    result = await availability_checker.check_availability_across_regions("/products/test")

    assert "🇺🇸 - ❌ (помилка)" in result
    assert "🇪🇺 - ❌ (помилка)" in result
    assert "🇬🇧 - ❌ (помилка)" in result
