"""
🧪 test_config_service.py — unit-тести для ConfigService

Перевіряє:
- Завантаження токенів з .env
- Роботу з кешем валют і fallback
- Завантаження / збереження ваги товарів
- Оновлення типів товарів та їх ваг
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import json
import pytest
from app.config.config_service import ConfigService



WEIGHT_FILE = "test_weights.json"
TYPE_FILE = "test_product_types.json"


@pytest.fixture(scope="module", autouse=True)
def setup_files():
    # Створюємо окремі файли для тестів, щоб не чіпати бойові
    ConfigService.WEIGHT_FILE = WEIGHT_FILE
    ConfigService.PRODUCT_TYPE_FILE = TYPE_FILE
    yield
    if os.path.exists(WEIGHT_FILE):
        os.remove(WEIGHT_FILE)
    if os.path.exists(TYPE_FILE):
        os.remove(TYPE_FILE)


def test_singleton_and_tokens():
    service = ConfigService()
    assert isinstance(service.telegram_token, str)
    assert isinstance(service.openai_api_key, str)


def test_currency_fallback():
    service = ConfigService()
    rate = service.fetch_exchange_rate("XYZ")
    assert isinstance(rate, float)
    assert rate == 42.0  # fallback


def test_weight_registration_and_update():
    service = ConfigService()
    service.register_weight("test-product", 0.5)
    weights = service.load_weight_data()
    assert weights.get("test-product") == 0.5

    service.update_weight_dict("test-product", 1.0)
    updated_weights = service.load_weight_data()
    assert updated_weights["test-product"] == 1.0


def test_product_type_handling():
    service = ConfigService()
    service.update_product_type("jersey", 0.3)

    types = service.load_product_types()
    assert types.get("jersey") == 0.3

    # Тест оновлення
    service.update_product_type("jersey", 0.5)
    types = service.load_product_types()
    assert types["jersey"] == 0.5
