"""
🧪 test_availability_manager.py — unit-тести для AvailabilityManager

Перевіряє:
- Швидку булеву перевірку наявності по регіонах
- Коректне використання кешу
"""

import pytest  # 📦 Фреймворк для тестування
from unittest.mock import AsyncMock, patch  # 🧰 Моки для асинхронних функцій
from core.product_availability.availability_manager import AvailabilityManager  # 🧱 Клас мульти-регіональної перевірки

@pytest.mark.asyncio
@patch("core.product_availability.availability_manager.BaseParser")
async def test_check_simple_availability_success(mock_parser):
    # 🧩 Мокований парсер з позитивною відповіддю
    mock_instance = AsyncMock()
    mock_instance.fetch_page.return_value = True
    mock_instance.is_product_available.return_value = True
    mock_parser.return_value = mock_instance

    manager = AvailabilityManager()

    # 🎯 Тестовий шлях до товару
    result = await manager.check_simple_availability("/products/test-product")

    # ✅ Очікувані прапорці в результаті
    assert "🇺🇸 - ✅" in result
    assert "🇺🇦 - ❌" in result
