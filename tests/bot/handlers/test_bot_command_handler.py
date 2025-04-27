"""
🧪 test_bot_command_handler.py — unit-тести для BotCommandHandler

Перевіряє:
- Показ курсу валют (mock)
- Ручну установку курсу (valid + invalid)
- Вивід довідки
- Відправку повідомлення (reply/callback)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.handlers.bot_command_handler import BotCommandHandler


@pytest.fixture
def mock_currency_manager():
    mock = MagicMock()
    mock.get_all_rates.return_value = {"USD": 42.5, "EUR": 46.0}
    return mock


@pytest.mark.asyncio
async def test_show_current_rate(mock_currency_manager):
    handler = BotCommandHandler(mock_currency_manager)

    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_update.callback_query = None
    mock_context = MagicMock()

    await handler.show_current_rate(mock_update, mock_context)
    mock_currency_manager.update_rate.assert_called_once()
    mock_currency_manager.get_all_rates.assert_called_once()
    mock_update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_custom_rate_valid(mock_currency_manager):
    handler = BotCommandHandler(mock_currency_manager)

    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_context = MagicMock()
    mock_context.args = ["USD", "42.5"]

    await handler.set_custom_rate(mock_update, mock_context)
    mock_currency_manager.set_rate_manually.assert_called_with("USD", 42.5)
    mock_update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_custom_rate_invalid(mock_currency_manager):
    handler = BotCommandHandler(mock_currency_manager)

    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_context = MagicMock()
    mock_context.args = ["USD"]  # ⛔️ Не вистачає значення

    await handler.set_custom_rate(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once_with(
        "❌ Формат команди: /set_rate USD 42.5"
    )


@patch("bot.handlers.bot_command_handler.Keyboard.help_menu", return_value="mock_keyboard")
@pytest.mark.asyncio
async def test_help_command(mock_keyboard, mock_currency_manager):
    handler = BotCommandHandler(mock_currency_manager)

    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_context = MagicMock()

    await handler.help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_message_reply_and_callback(mock_currency_manager):
    handler = BotCommandHandler(mock_currency_manager)
    update_msg = MagicMock()
    update_msg.message = AsyncMock()
    update_msg.callback_query = None

    update_cb = MagicMock()
    update_cb.message = None
    update_cb.callback_query = AsyncMock()

    await handler._send_message(update_msg, "Test reply")
    await handler._send_message(update_cb, "Test callback")

    update_msg.message.reply_text.assert_awaited_once_with("Test reply", parse_mode="HTML", reply_markup=None)
    update_cb.callback_query.edit_message_text.assert_awaited_once_with("Test callback", parse_mode="HTML", reply_markup=None)
