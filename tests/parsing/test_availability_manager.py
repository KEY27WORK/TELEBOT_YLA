import pytest
from unittest.mock import patch
from product_availability.availability_manager import AvailabilityManager
import pytest

pytest_plugins = "pytest_asyncio"

@pytest.mark.asyncio
@patch('core.parsing.json_ld_parser.JsonLdAvailabilityParser.extract_color_size_availability')
async def test_check_and_aggregate(mock_extract):
    mock_extract.return_value = {
        'blue': {'S': True, 'M': True},
        'red': {'L': True}
    }
    manager = AvailabilityManager()
    result = await manager.check_and_aggregate("/product-path")
    assert 'blue' in result
    assert 'red' in result

@pytest.mark.asyncio
@patch('core.parsing.base_parser.BaseParser.is_product_available')
async def test_check_simple_availability(mock_is_available):
    mock_is_available.return_value = True
    manager = AvailabilityManager()
    result = await manager.check_simple_availability("/product-path")
    assert "✅" in result
    assert "🇺🇦" in result