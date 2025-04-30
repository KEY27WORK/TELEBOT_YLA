"""
🧪 Тести для region_utils.py

Перевіряються:
- Визначення валюти з URL (USD, EUR, GBP)
- Визначення регіону з emoji
- Обробка помилок при невідомому URL
"""

# 📦 Стандартні
import pytest

# 🧰 Утиліти
from utils.region_utils import get_currency_from_url, get_region_from_url


@pytest.mark.parametrize("url, expected_currency", [
    ("https://youngla.com/products/item", "USD"),
    ("https://www.youngla.com/products/item", "USD"),
    ("https://eu.youngla.com/products/item", "EUR"),
    ("https://uk.youngla.com/products/item", "GBP"),
])
def test_get_currency_from_url(url, expected_currency):
    assert get_currency_from_url(url) == expected_currency


@pytest.mark.parametrize("url, expected_region", [
    ("https://youngla.com/products/item", "US 🇺🇸"),
    ("https://eu.youngla.com/products/item", "EU 🇪🇺"),
    ("https://uk.youngla.com/products/item", "UK 🇬🇧"),
])
def test_get_region_from_url(url, expected_region):
    assert get_region_from_url(url) == expected_region


def test_unknown_url_raises_value_error():
    with pytest.raises(ValueError) as exc_info:
        get_currency_from_url("https://unknown.youngla.net/item")
    assert "Невідомий регіон" in str(exc_info.value)
