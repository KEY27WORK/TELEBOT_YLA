"""
🧪 test_price_flow.py — інтеграційний тест для ProductHandler + PriceCalculationHandler

Перевіряє:
- Розрахунок повного повідомлення з ціною
- Виклик калькулятора та форматування
- Коректний вивід валют і блоків доставки/собівартості
"""

import pytest
from bot.handlers.product_collection_handler import ProductHandler
from core.currency.currency_manager import CurrencyManager

@pytest.mark.asyncio
async def test_product_price_flow():
    # 🔧 Ініціалізуємо залежності
    currency_manager = CurrencyManager()
    handler = ProductHandler(currency_manager=currency_manager)

    # Вхідні тестові дані
    title = "W214 Oversized Tee"
    price = 28.0
    weight = 0.6
    image_url = "https://test.com/image.jpg"
    currency = "USD"

    # 🔍 Виклик розрахунку ціни
    message = await handler.price_handler.calculate_and_format(
        title=title,
        price=price,
        weight=weight,
        image_url=image_url,
        currency=currency
    )

    # 🔍 Перевіряємо ключові блоки
    assert "💵 Ціна в $:" in message
    assert "💲 Собівартість:" in message
    assert "📦 Доставка:" in message
    assert "💸 Ціна для клієнта:" in message
    assert "💰 Прибуток:" in message
    assert "$" in message and "₴" in message
    assert image_url in message or "img" in message.lower()
