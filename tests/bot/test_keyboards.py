"""
🧪 test_keyboards.py — unit-тести для модуля Keyboard

Перевіряє:
- Створення головного меню
- Inline-меню курсу валют
- Inline-меню допомоги
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards import Keyboard


def test_main_menu_structure():
    result = Keyboard.main_menu()
    assert isinstance(result, ReplyKeyboardMarkup)
    row0 = [btn.text for btn in result.keyboard[0]]
    row_last = [btn.text for btn in result.keyboard[-1]]

    assert row0 == ["🔗 Вставляти посилання товарів", "📦 Мої замовлення"]
    assert row_last == ["⏹️ Вимкнути режим"]
    assert result.resize_keyboard is True


def test_currency_menu_buttons():
    result = Keyboard.currency_menu()
    assert isinstance(result, InlineKeyboardMarkup)
    buttons = [btn for row in result.inline_keyboard for btn in row]
    labels = [btn.text for btn in buttons]
    callbacks = [btn.callback_data for btn in buttons]

    assert "📊 Показати курс" in labels
    assert "show_rate" in callbacks
    assert "✏️ Встановити курс" in labels
    assert "set_rate" in callbacks


def test_help_menu_buttons():
    result = Keyboard.help_menu()
    assert isinstance(result, InlineKeyboardMarkup)
    texts = [btn.text for row in result.inline_keyboard for btn in row]
    data = [btn.callback_data for row in result.inline_keyboard for btn in row]

    assert "📝 FAQ" in texts
    assert "📖 Як користуватись ботом?" in texts
    assert "📞 Зв'язатися з підтримкою" in texts
    assert "faq" in data
    assert "help_usage" in data
    assert "help_support" in data
