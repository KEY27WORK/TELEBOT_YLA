"""
🧪 test_availability_manager.py — unit-тести для AvailabilityManager

Перевіряє:
- Швидку булеву перевірку наявності по регіонах
- Коректне використання кешу
- Генерацію звітів через AvailabilityReportBuilder
"""

import pytest
from unittest.mock import AsyncMock, patch
from core.product_availability.availability_manager import AvailabilityManager


@pytest.mark.asyncio
@patch("core.product_availability.availability_manager.BaseParser")
async def test_check_simple_availability_success(mock_parser):
    mock_instance = AsyncMock()
    mock_instance.fetch_page.return_value = True
    mock_instance.is_product_available.return_value = True
    mock_parser.return_value = mock_instance

    manager = AvailabilityManager()
    result = await manager.check_simple_availability("/products/test-product")

    assert "🇺🇸 - ✅" in result
    assert "🇪🇺 - ✅" in result
    assert "🇬🇧 - ✅" in result
    assert "🇺🇦 - ❌" in result


@pytest.mark.asyncio
@patch("core.product_availability.availability_manager.BaseParser")
async def test_check_simple_availability_cache(mock_parser):
    mock_instance = AsyncMock()
    mock_instance.fetch_page.return_value = True
    mock_instance.is_product_available.return_value = True
    mock_parser.return_value = mock_instance

    manager = AvailabilityManager()
    path = "/products/cached-product"

    # 1-й виклик — викликає fetch_page
    await manager.check_simple_availability(path)

    # 2-й виклик — має повернутись з кешу
    result = await manager.check_simple_availability(path)

    assert "🇺🇸" in result
    mock_instance.fetch_page.assert_called_once()  # fetch_page має бути лише один раз

@pytest.mark.asyncio
@patch("core.product_availability.availability_manager.BaseParser")
async def test_get_availability_report_builds_and_caches(mock_parser):
    # 🧩 Мок парсера, що повертає доступний товар у кожному регіоні
    mock_instance = AsyncMock()
    mock_instance.fetch_page.return_value = True
    mock_instance.get_stock_data.return_value = {
        "Black": {"S": True, "M": False},
        "White": {"M": True}
    }
    mock_parser.return_value = mock_instance

    manager = AvailabilityManager()
    path = "/products/testing-report"

    # Перший виклик — кеш ще порожній
    region_checks_1, public_1, admin_1 = await manager.get_availability_report(path)

    # Другий виклик — має прийти з кешу
    region_checks_2, public_2, admin_2 = await manager.get_availability_report(path)

    assert region_checks_1 == region_checks_2
    assert public_1 == public_2
    assert admin_1 == admin_2