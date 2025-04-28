"""🧪 test_product_collection_handler.py — unit-тести для CollectionHandler

🔍 Перевіряє:
- ✅ Вивід інформації про регіон (send_region_info)
- ✅ Парсинг колекцій та обробку посилань (handle_collection)
- ✅ Виклик handle_url у ProductHandler для кожного товару (process_each_product)

📦 Ізоляція:
- CollectionParser — моканий
- ProductHandler — моканий

🎯 Ціль:
Переконатися, що CollectionHandler виконує основну логіку парсингу колекцій правильно,
і делегує обробку кожного товару до ProductHandler.
"""

# 🧪 Тестування
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# 🤖 Обробник, який тестується
from bot.handlers.product_collection_handler import CollectionHandler


@pytest.fixture
def mock_update():
    mock = MagicMock()
    mock.message.text = "https://some.collection"
    mock.message.reply_text = AsyncMock()
    return mock


@pytest.fixture
def mock_context():
    return MagicMock()


@patch("bot.handlers.product_collection_handler.CollectionParser")
@pytest.mark.asyncio
async def test_handle_collection_success(mock_parser_class, mock_update, mock_context):
    # 🧪 Моки
    mock_parser = MagicMock()
    mock_parser.parser.get_currency.return_value = "USD"
    mock_parser.extract_product_links = AsyncMock(return_value=[
        "https://product1", "https://product2"
    ])
    mock_parser_class.return_value = mock_parser

    # 🔧 CollectionHandler с мокнутым ProductHandler
    mock_product_handler = MagicMock()
    mock_product_handler.handle_url = AsyncMock()

    handler = CollectionHandler(product_handler=mock_product_handler)

    await handler.handle_collection(mock_update, mock_context)

    # ✅ Проверки
    mock_update.message.reply_text.assert_any_call(
        "🔍 Знайдено 2 товарів. Починаю обробку..."
    )
    assert mock_product_handler.handle_url.await_count == 2


@pytest.mark.asyncio
async def test_send_region_info(mock_update):
    handler = CollectionHandler()
    await handler.send_region_info(mock_update, "EUR")
    mock_update.message.reply_text.assert_awaited_once_with(
        "🌍 Регіон колекції: <b>EUR</b>", parse_mode="HTML"
    )


@pytest.mark.asyncio
async def test_process_each_product_calls_product_handler(mock_update, mock_context):
    mock_product_handler = MagicMock()
    mock_product_handler.handle_url = AsyncMock()

    handler = CollectionHandler(product_handler=mock_product_handler)

    urls = ["https://one.com", "https://two.com"]
    await handler.process_each_product(mock_update, mock_context, urls)

    assert mock_product_handler.handle_url.await_count == 2
    mock_product_handler.handle_url.assert_any_await(mock_update, mock_context, "https://one.com", update_currency=False)

