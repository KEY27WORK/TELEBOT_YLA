import pytest
import asyncio
from app.cores.parsers.availability_aggregator import AvailabilityAggregator

@pytest.mark.asyncio
async def test_merge_global_stock_basic():
    # Мокаем данные по регионам
    aggregated = {
        "us": {
            "Black Wash": {"S": True, "M": True, "L": True},
            "Grey Wash": {"S": False, "M": True}
        },
        "eu": {
            "Black Wash": {"S": False, "M": True, "L": False},
            "Grey Wash": {"S": True, "M": True}
        },
        "uk": {
            "Black Wash": {"S": True, "M": False, "L": True},
            "Grey Wash": {"S": True, "M": False}
        },
        "ua": {}
    }

    result = AvailabilityAggregator.merge_global_stock(aggregated)

    assert result == {
        "Black Wash": {"S": True, "M": True, "L": True},
        "Grey Wash": {"S": True, "M": True}
    }


@pytest.mark.asyncio
async def test_aggregate_availability_formatting(monkeypatch):
    """
    Тестируем финальный форматированный вывод
    """

    async def mock_fetch_region_data(region_code, product_path):
        # Возвращаем одинаковые данные для всех регионов
        data = {
            "Black Wash": {"S": True, "M": False, "L": True},
            "Grey Wash": {"S": False, "M": True}
        }
        return region_code, data

    monkeypatch.setattr(AvailabilityAggregator, "fetch_region_data", mock_fetch_region_data)

    product_path = "/products/test-item"
    formatted = await AvailabilityAggregator.aggregate_availability_formatted(product_path)

    # Просто проверяем, что форматированная строка содержит нужные цвета
    assert "Black Wash" in formatted
    assert "Grey Wash" in formatted
    assert "S" in formatted
    assert "M" in formatted or "🚫" in formatted