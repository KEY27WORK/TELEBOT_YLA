"""🧪 test_price_calculation_handler.py — Unit-тести для PriceCalculationHandler

🔍 Перевіряє:
- Побудову фінального повідомлення з ціною
- Визначення валюти/регіону
- Формування блоків:
  • Заголовок
  • Ціна продажу (у кількох валютах)
  • Доставка (локальна + Meest)
  • Собівартість
  • Накрутка
  • Прибуток

✅ Принципи:
- Чіткий поділ тестів за функціональністю
- Ізоляція залежностей через mock
"""

# 🧪 Тестування
import pytest
from unittest.mock import MagicMock

# 🧠 Обробник
from bot.handlers.price_calculation_handler import PriceCalculationHandler


@pytest.fixture
def pricing_mock():
    return {
        "sale_price_usd": 78.9,
        "sale_price_rounded_usd": 80.0,
        "round_usd": 1.1,

        "sale_price_eur": 72.2,
        "sale_price_rounded_eur": 75.0,
        "round_eur": 2.8,

        "sale_price_uah": 3133,
        "sale_price_rounded_uah": 3190,
        "round_uah": 1.8,

        "us_delivery_usd": 5.9,
        "meest_delivery_usd": 10.2,
        "delivery_price_usd": 16.1,

        "us_delivery_eur": 5.5,
        "meest_delivery_eur": 9.7,
        "delivery_price_eur": 15.2,

        "us_delivery_uah": 248,
        "meest_delivery_uah": 423,
        "delivery_price_uah": 671,

        "cost_price_without_delivery_usd": 60.0,
        "cost_price_usd": 76.1,

        "cost_price_without_delivery_eur": 56.0,
        "cost_price_eur": 71.2,

        "cost_price_without_delivery_uah": 2600,
        "cost_price_uah": 3288,

        "markup": 30.5,
        "markup_adjustment": 5.5,

        "profit_usd": 2.8,
        "profit_with_round_usd": 3.9,

        "profit_eur": 1.0,
        "profit_with_round_eur": 3.8,

        "profit_uah": 88,
        "profit_with_round_uah": 152,

        "weight_lbs": 1.3,
        "usd_rate": 39.7
    }


def test_get_region_display():
    handler = PriceCalculationHandler(MagicMock())

    assert handler._get_region_display("USD") == "🇺🇸 США"
    assert handler._get_region_display("EUR") == "🇪🇺 Європа"
    assert handler._get_region_display("PLN") == "🇵🇱 Польща"
    assert handler._get_region_display("ABC") == "Невідомо"


def test_build_price_message(pricing_mock):
    handler = PriceCalculationHandler(MagicMock())
    result = handler._build_price_message(
        "Test Hoodie",
        pricing_mock,
        weight=1.3,
        image_url="https://image.com/item.jpg",
        currency="USD"
    )

    assert "💵 Ціна продажу" in result
    assert "📦 Локальна доставка" in result
    assert "🏷️ Собівартість" in result
    assert "📈 % Процент накрутки" in result
    assert "📊 Чистий прибуток" in result
