"""
🧪 test_formatter.py — unit-тести для форматера ColorSizeFormatter

Перевіряє:
- Форматування наявності товарів для Telegram-повідомлень
- Форматування для адміністративної панелі
"""

import pytest  # 📦 Фреймворк для тестування
from core.product_availability.formatter import ColorSizeFormatter  # 🧱 Клас для форматування доступності

def test_format_color_size_availability():
    # 🎯 Симуляція наявності по кольорах і розмірах
    color_data = {
        "Black": {"S": True, "M": False, "L": True},
        "White": {"S": False, "M": False}
    }
    # 📤 Виклик функції форматування
    result = ColorSizeFormatter.format_color_size_availability(color_data)

    # ✅ Очікувані частини рядка
    assert "• Black: S, L" in result
    assert "• White: 🚫" in result

def test_format_admin_availability():
    # 🛠 Фейкові дані по наявності у різних регіонах
    availability = {
        "Navy": {
            "us": ["M", "L"],
            "eu": ["M"],
            "uk": [],
            "ua": ["L"]
        }
    }
    # 📌 Повний список розмірів
    all_sizes_map = {"Navy": ["S", "M", "L"]}
    
    result = ColorSizeFormatter.format_admin_availability(availability, all_sizes_map)

    # 🧪 Очікувана вивідна структура
    assert "S," in result
    assert "🇺🇸 - 🚫" in result
    assert "🇪🇺 - ✅" in result