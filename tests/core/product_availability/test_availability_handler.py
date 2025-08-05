"""
🧪 test_availability_handler.py — unit-тести для AvailabilityHandler

Перевіряє:
- Обробку URL посилання
- Вивід Telegram-повідомлень (зображення, публічний формат, адмін формат)
"""

import pytest  # 📦 Фреймворк для тестування
from unittest.mock import AsyncMock, patch, MagicMock  # 🧰 Моки
from app.infrastructure.availability.availability_handler import AvailabilityHandler  # 🧱 Хендлер для Telegram-бота

@pytest.mark.asyncio
@patch("core.product_availability.availability_handler.BaseParser")
@patch("core.product_availability.availability_handler.AvailabilityManager")
async def test_handle_availability(mock_manager_class, mock_parser_class):
    # 🔧 Імітуємо об'єкти Telegram update/context
    mock_update = MagicMock()
    mock_update.message.reply_photo = AsyncMock()
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()

    # 📦 Мокований парсер товару (назва, зображення)
    mock_parser = AsyncMock()
    mock_parser.parse.return_value = {"title": "Test Product", "image_url": "http://img.jpg"}
    mock_parser_class.return_value = mock_parser

    # 🔁 Мокований AvailabilityManager
    mock_manager = AsyncMock()
    mock_manager.get_availability_report.return_value = (
        "🇺🇸 - ✅\n🇪🇺 - ❌\n🇬🇧 - ✅\n🇺🇦 - ❌",
        "• Black: M, L",
        "Black:\n🇺🇸: M\n🇬🇧: L"
    )
    mock_manager_class.return_value = mock_manager

    # 🧪 Запускаємо метод і перевіряємо Telegram-вивід
    handler = AvailabilityHandler()
    await handler.handle_availability(mock_update, mock_context, "https://www.youngla.com/products/test-product")

    # ✅ Перевіряємо, що всі повідомлення були відправлені
    mock_update.message.reply_photo.assert_awaited_once()
    mock_update.message.reply_text.assert_awaited()
