"""
🧪 test_link_handler.py — unit-тест для LinkHandler

Перевіряє:
- Визначення режиму (товар, колекція, розрахунок, таблиця)
- Виклик відповідного обробника
- Відповідь у разі помилки
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from core.parsers.link_handler import LinkHandler
from core.currency.currency_manager import CurrencyManager


@pytest.fixture
def handler():
    return LinkHandler(
        currency_manager=CurrencyManager(),
        product_handler=AsyncMock(),
        collection_handler=AsyncMock(),
        size_chart_handler=AsyncMock(),
        price_calculator=AsyncMock()
    )


def create_mock_update(text):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_product_link_auto_mode(handler):
    update = create_mock_update("https://www.youngla.com/products/some-product")
    context = MagicMock()
    context.user_data = MagicMock()
    context.user_data.get = MagicMock(return_value=None)

    await handler.handle_link(update, context)

    handler.product_handler.handle_url.assert_awaited_once()


@pytest.mark.asyncio
async def test_collection_link_auto_mode(handler):
    update = create_mock_update("https://eu.youngla.com/collections/new-launch")
    context = MagicMock()
    context.user_data = {}

    await handler.handle_link(update, context)

    assert context.user_data["mode"] == "collection"
    handler.collection_handler.handle_collection.assert_awaited_once()


@pytest.mark.asyncio
async def test_size_chart_mode_product(handler):
    update = create_mock_update("https://uk.youngla.com/products/abc")
    context = MagicMock()
    context.user_data = {"mode": "size_chart"}

    await handler.handle_link(update, context)

    handler.size_chart_handler.size_chart_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_size_chart_mode_invalid(handler):
    update = create_mock_update("https://not.youngla.com/about")
    context = MagicMock()
    context.user_data = {"mode": "size_chart"}

    await handler.handle_link(update, context)

    update.message.reply_text.assert_awaited_with("❌ Це не схоже на посилання на товар. Перевір, будь ласка.")


@pytest.mark.asyncio
async def test_price_calc_mode_product(handler):
    update = create_mock_update("https://www.youngla.com/products/xyz")
    context = MagicMock()
    context.user_data = {"mode": "price_calculation"}

    await handler.handle_link(update, context)

    handler.price_calculator.handle_price_calculation.assert_awaited_once()



@pytest.mark.asyncio
async def test_price_calc_mode_invalid(handler):
    update = create_mock_update("https://google.com")
    context = MagicMock()
    context.user_data = {"mode": "price_calculation"}

    await handler.handle_link(update, context)

    update.message.reply_text.assert_awaited_with("❌ Це не посилання на товар. Перевір, будь ласка.")
