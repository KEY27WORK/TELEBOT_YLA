"""🧪 test_calculator.py — unit-тести для калькуляторів цін

Перевіряє:
- Правильність розрахунків для кожного калькулятора (USD, GBP, EUR, PLN)
- Округлення, знижку, накрутку, доставку
- Роботу PriceCalculatorFactory
"""

import pytest
from app.infrastructure.currency.currency_manager import CurrencyManager
from app.cores.calculator.calculator import (
    PriceCalculatorUSD,
    PriceCalculatorGBP,
    PriceCalculatorGermany,
    PriceCalculatorPoland,
    PriceCalculatorFactory
)

# 🧪 Тестові курси валют
mock_rates = {
    "USD": 40.0,
    "EUR": 43.0,
    "GBP": 47.0,
    "PLN": 9.5,
}

@pytest.fixture
def mock_currency_manager():
    mock = CurrencyManager()
    mock.get_all_rates = lambda: mock_rates
    mock.convert = lambda amount, from_, to, rates: round(rates[to] / rates[from_], 4)
    return mock


# -------------------
# 🇺🇸 USD калькулятор
# -------------------

def test_usd_calculator_basic(mock_currency_manager):
    calc = PriceCalculatorUSD(mock_rates, {"USD": 0.93})
    result = calc.calculate(price_usd=50, weight=2.0, currency="USD")

    assert "sale_price_usd" in result
    assert result["sale_price_usd"] > result["cost_price_usd"]
    assert result["delivery_price_usd"] > 0
    assert result["markup"] > 0


# -------------------
# 🇬🇧 GBP калькулятор
# -------------------

def test_gbp_calculator_basic(mock_currency_manager):
    calc = PriceCalculatorGBP(mock_rates, {
        "GBP": mock_currency_manager.convert(1, "GBP", "USD", mock_rates)
    }, {
        "USD": mock_currency_manager.convert(1, "USD", "EUR", mock_rates)
    })
    result = calc.calculate(price_gbp=60, weight=1.5, currency="GBP")

    assert "sale_price_gbp" in result
    assert result["sale_price_usd"] > result["cost_price_usd"]
    assert result["markup_adjustment"] in (-3, 0, 3)


# --------------------
# 🇩🇪 EUR калькулятор
# --------------------

def test_eur_calculator_basic(mock_currency_manager):
    calc = PriceCalculatorGermany(mock_rates, {
        "EUR": mock_currency_manager.convert(1, "EUR", "USD", mock_rates)
    }, {
        "USD": mock_currency_manager.convert(1, "USD", "EUR", mock_rates)
    })
    result = calc.calculate(price_eur=80, weight=3.0, currency="EUR")

    assert "sale_price_eur" in result
    assert result["profit_eur"] > 0
    assert result["delivery_price_usd"] > 0


# ----------------------
# 🇵🇱 PLN калькулятор
# ----------------------

def test_pln_calculator_basic(mock_currency_manager):
    calc = PriceCalculatorPoland(mock_rates, {
        "PLN": mock_currency_manager.convert(1, "PLN", "USD", mock_rates)
    }, {
        "USD": mock_currency_manager.convert(1, "USD", "EUR", mock_rates),
        "PLN": mock_currency_manager.convert(1, "EUR", "PLN", mock_rates),  # ✅ добавляем этот ключ
    })

    result = calc.calculate(price_pln=200, weight=2.2, currency="PLN")

    assert "sale_price_pln" in result
    assert result["profit_uah"] > 0
    assert result["cost_price_pln"] > 0


# --------------------------
# 🏭 Фабрика калькуляторів
# --------------------------

def test_calculator_factory_usd(mock_currency_manager):
    factory = PriceCalculatorFactory(mock_currency_manager)
    calc = factory.get_calculator("USD")
    assert isinstance(calc, PriceCalculatorUSD)

def test_calculator_factory_gbp(mock_currency_manager):
    factory = PriceCalculatorFactory(mock_currency_manager)
    calc = factory.get_calculator("GBP")
    assert isinstance(calc, PriceCalculatorGBP)

def test_calculator_factory_eur(mock_currency_manager):
    factory = PriceCalculatorFactory(mock_currency_manager)
    calc = factory.get_calculator("EUR")
    assert isinstance(calc, PriceCalculatorGermany)

def test_calculator_factory_pln(mock_currency_manager):
    factory = PriceCalculatorFactory(mock_currency_manager)
    calc = factory.get_calculator("PLN")
    assert isinstance(calc, PriceCalculatorPoland)

def test_factory_unsupported_currency(mock_currency_manager):
    factory = PriceCalculatorFactory(mock_currency_manager)
    with pytest.raises(ValueError):
        factory.get_calculator("JPY")
