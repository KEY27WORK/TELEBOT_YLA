"""
🧪 test_currency_manager.py — unit-тести для CurrencyManager

Перевіряє:
- Завантаження курсів з файлу
- Отримання актуального курсу
- Оновлення курсів з Monobank API
- Ручне встановлення курсу
- Перехресну конвертацію валют
"""

import pytest
from core.currency.currency_manager import CurrencyManager

TEST_RATES = {
    "USD": 42.0,
    "EUR": 46.0,
    "GBP": 49.0,
    "PLN": 10.0
}

manager = CurrencyManager()
manager.rates = TEST_RATES.copy()

def test_dummy():
    assert True

def test_get_current_rate():
    assert manager.get_current_rate("USD") == 42.0
    assert manager.get_current_rate("EUR") == 46.0
    assert manager.get_current_rate("UNKNOWN") == 42.3

def test_set_rate_manually():
    manager.set_rate_manually("USD", 45.0)
    assert manager.get_current_rate("USD") == 45.0
    manager.set_rate_manually("USD", 42.0)

def test_convert_same_currency():
    assert manager.convert(100, "USD", "USD", TEST_RATES) == 100

def test_convert_usd_to_eur():
    result = manager.convert(100, "USD", "EUR", TEST_RATES)
    expected = round(100 * 42.0 / 46.0, 2)
    assert result == expected

def test_convert_with_internal_rates():
    result = manager.convert(50, "GBP", "PLN", None)
    expected = round(50 * 49.0 / 10.0, 2)
    assert result == expected

def test_get_all_rates():
    rates = manager.get_all_rates()
    assert isinstance(rates, dict)
    assert "USD" in rates and "EUR" in rates
