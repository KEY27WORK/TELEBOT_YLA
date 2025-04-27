"""
🧪 test_main.py — unit-тести для TelegramBot (main.py)

Перевіряє:
- Ініціалізацію основного бота та залежностей
- Команду /start (відповідь з меню)
- Обробку inline-кнопок (наприклад, 'show_rate', 'help_usage')
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bot.main import TelegramBot


@pytest.fixture
def bot_instance():
    """🔧 Фікстура для створення екземпляру TelegramBot."""
    return TelegramBot()


def test_bot_initialization(bot_instance):
    """✅ Перевіряє, що TelegramBot створюється з усіма залежностями."""
    assert bot_instance.currency_manager
    assert bot_instance.product_handler
    assert bot_instance.link_handler
    assert bot_instance.menu_handler


@pytest.mark.asyncio
async def test_start_command_sends_menu(bot_instance):
    """📋 /start — бот надсилає привітання + меню."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await bot_instance.start(update, context)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert "YoungLA Ukraine" in args[0]
    assert kwargs.get("reply_markup")


@pytest.mark.asyncio
@patch("bot.main.BotCommandHandler.show_current_rate", new_callable=AsyncMock)
async def test_button_handler_show_rate(mock_show, bot_instance):
    """💱 callback show_rate — показ курсу."""
    query = MagicMock()
    query.data = "show_rate"
    query.answer = AsyncMock()

    update = MagicMock()
    update.callback_query = query
    context = MagicMock()

    await bot_instance.button_handler(update, context)

    query.answer.assert_awaited_once()
    mock_show.assert_awaited_once()


@pytest.mark.asyncio
async def test_button_handler_help_usage(bot_instance):
    """📖 callback help_usage — інструкція для користувача."""
    query = MagicMock()
    query.data = "help_usage"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock()
    update.callback_query = query
    context = MagicMock()

    await bot_instance.button_handler(update, context)

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()
    args, kwargs = query.edit_message_text.call_args
    assert "Як користуватись ботом" in args[0]
    assert kwargs.get("parse_mode") == "HTML"
