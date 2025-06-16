
import pytest
from core.parsing.regional_availability_checker import RegionalAvailabilityChecker

@pytest.mark.asyncio
async def test_check_basic():
    result = await RegionalAvailabilityChecker.check_basic('/path/to/product')
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_check_full():
    result = await RegionalAvailabilityChecker.check_full('/path/to/product')
    assert isinstance(result, dict)


def test_aggregate_availability():
    input_data = {
        "US": {"size": "M", "availability": True},
        "EU": {"size": "L", "availability": False}
    }
    result = RegionalAvailabilityChecker.aggregate_availability(input_data)
    assert isinstance(result, dict)

