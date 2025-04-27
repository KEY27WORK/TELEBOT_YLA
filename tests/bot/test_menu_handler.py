""" 🧪 test_menu_handler.py — тести для MenuHandler

Перевіряє:
- Обробку кожного пункту головного меню
- Збереження режимів у user_data
- Надсилання відповідних повідомлень
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.menu_handler import MenuHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup
from bot.keyboards import Keyboard


@pytest.mark.asyncio
@pytest.mark.parametrize("text, expected_mode, expected_reply", [
    ("🔗 Вставляти посилання товарів", "product", "✅ Режим вставки посилань на товари активовано."),
    ("📚 Режим колекцій", "collection", "✅ Режим колекцій активовано."),
    ("📏 Таблиця розмірів", "size_chart", "📏 Режим таблиць розмірів активовано."),
    ("🧮 Режим розрахунку товару", "price_calculation", "🧮 Режим розрахунку ціни активовано."),
])
async def test_mode_switching(text, expected_mode, expected_reply):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {}

    await MenuHandler.handle_menu(update, context)

    assert context.user_data["mode"] == expected_mode
    update.message.reply_text.assert_awaited()
    assert expected_reply in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_show_orders():
    update = MagicMock()
    update.message.text = "📦 Мої замовлення"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await MenuHandler.handle_menu(update, context)

    update.message.reply_text.assert_awaited_with("📦 У вас поки що немає замовлень.")


@pytest.mark.asyncio
async def test_currency_menu():
    update = MagicMock()
    update.message.text = "💱 Курс валют"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await MenuHandler.handle_menu(update, context)

    args, kwargs = update.message.reply_text.call_args
    assert "💱 Виберіть дію з курсом валют" in args[0]
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_help_menu():
    update = MagicMock()
    update.message.text = "❓ Допомога"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await MenuHandler.handle_menu(update, context)

    args, kwargs = update.message.reply_text.call_args
    assert "🆘 Чим можу допомогти" in args[0]
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_turn_off_mode():
    update = MagicMock()
    update.message.text = "⏹️ Вимкнути режим"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {"mode": "product"}

    await MenuHandler.handle_menu(update, context)

    assert context.user_data["mode"] is None
    args, kwargs = update.message.reply_text.call_args
    assert "⏹️ Усі режими вимкнено" in args[0]
    assert isinstance(kwargs["reply_markup"], ReplyKeyboardMarkup)


@pytest.mark.asyncio
async def test_unknown_command():
    update = MagicMock()
    update.message.text = "🥩 М'ясо"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await MenuHandler.handle_menu(update, context)

    update.message.reply_text.assert_awaited_with("❓ Ця опція поки що не підтримується.")
