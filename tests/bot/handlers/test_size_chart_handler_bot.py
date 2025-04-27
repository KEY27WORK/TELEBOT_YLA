"""
🧪 test_size_chart_handler_bot.py — unit-тести для SizeChartHandlerBot

Перевіряє:
- Обробку команди /size_chart
- Завантаження або використання HTML
- Генерацію таблиці розмірів
- Відправку зображення
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from bot.handlers.size_chart_handler_bot import SizeChartHandlerBot


@pytest.mark.asyncio
async def test_resolve_url_from_args():
    update = MagicMock()
    context = MagicMock()
    context.args = ["https://link.com"]

    result = await SizeChartHandlerBot._resolve_url(update, context)
    assert result == "https://link.com"


@pytest.mark.asyncio
async def test_resolve_url_missing():
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []

    result = await SizeChartHandlerBot._resolve_url(update, context)
    assert result is None
    update.message.reply_text.assert_awaited_once()


@patch("bot.handlers.size_chart_handler_bot.ProductParser")
@pytest.mark.asyncio
async def test_get_page_source_from_parser(mock_parser_class):
    parser_mock = MagicMock()
    parser_mock.page_source = "<html>source</html>"
    parser_mock.parser.fetch_page = AsyncMock()
    mock_parser_class.return_value = parser_mock

    result = await SizeChartHandlerBot._get_page_source("https://link.com")
    assert result == "<html>source</html>"
    parser_mock.parser.fetch_page.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_page_source_direct_html():
    result = await SizeChartHandlerBot._get_page_source("https://link.com", "<html>preloaded</html>")
    assert result == "<html>preloaded</html>"


@patch("bot.handlers.size_chart_handler_bot.SizeChartHandler")
@pytest.mark.asyncio
async def test_generate_size_chart_success(mock_chart_handler):
    mock_chart = MagicMock()
    mock_chart.process_size_chart = AsyncMock(return_value="image.png")
    mock_chart_handler.return_value = mock_chart

    result = await SizeChartHandlerBot._generate_size_chart("url", "<html>")
    assert result == "image.png"


@patch("builtins.open", new_callable=mock_open, read_data=b"imgdata")
@pytest.mark.asyncio
async def test_send_size_chart_image_success(mock_file):
    update = MagicMock()
    update.message.reply_photo = AsyncMock()

    await SizeChartHandlerBot._send_size_chart_image(update, "dummy/path/image.png")
    update.message.reply_photo.assert_awaited_once()


@patch("bot.handlers.size_chart_handler_bot.SizeChartHandlerBot._get_page_source", new_callable=AsyncMock, return_value=None)
@pytest.mark.asyncio
async def test_size_chart_command_no_source(mock_source):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["https://link.com"]

    await SizeChartHandlerBot.size_chart_command(update, context)
    update.message.reply_text.assert_awaited_with("❌ Не вдалося завантажити сторінку товару.")


@patch("bot.handlers.size_chart_handler_bot.SizeChartHandlerBot._get_page_source", new_callable=AsyncMock, return_value="<html>")
@patch("bot.handlers.size_chart_handler_bot.SizeChartHandlerBot._generate_size_chart", new_callable=AsyncMock, return_value=None)
@pytest.mark.asyncio
async def test_size_chart_command_no_chart(mock_chart, mock_source):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["https://link.com"]

    await SizeChartHandlerBot.size_chart_command(update, context)
    update.message.reply_text.assert_awaited_with("⚠️ Не знайдено таблицю розмірів.")
