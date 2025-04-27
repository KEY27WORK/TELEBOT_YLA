""" 🧪 test_meest_delivery_service.py — unit-тести для MeestDeliveryService

Перевіряє:
- Розрахунок доставки по країнах (US, UK, Germany, Poland)
- Правильність тарифів
- Обробку непідтримуваних конфігурацій
"""

import pytest
from core.calculator.meest_delivery_service import MeestDeliveryService


@pytest.mark.parametrize("weight,expected", [
    (0.3, 5.90),
    (0.6, 8.19),  # ✅ минимальный порог
    (2.0, pytest.approx(8.69 * 2.0, abs=0.01))
])
def test_us_air_price(weight, expected):
    result = MeestDeliveryService.get_price("US", "air", "courier", weight)
    assert result == expected


@pytest.mark.parametrize("weight,expected", [
    (1.5, pytest.approx(8.05 + 1.45 * 1.5, abs=0.01)),
    (3.0, pytest.approx(5.15 + 2.55 * 3.0, abs=0.01)),
    (11.0, pytest.approx(5.15 + 2.45 * 11.0, abs=0.01))
])
def test_uk_air_price(weight, expected):
    result = MeestDeliveryService.get_price("UK", "air", "courier", weight)
    assert result == expected


@pytest.mark.parametrize("weight,expected", [
    (0.4, 5.00),
    (2.0, 9.50),
    (3.5, pytest.approx(4.50 * 3.5, abs=0.01)),
    (7.0, pytest.approx(3.75 * 7.0, abs=0.01)),
    (15.0, pytest.approx(3.50 * 15.0, abs=0.01)),
    (25.0, pytest.approx(3.30 * 25.0, abs=0.01))
])
def test_germany_air_price(weight, expected):
    result = MeestDeliveryService.get_price("Germany", "air", "courier", weight)
    assert result == expected


@pytest.mark.parametrize("weight,expected", [
    (0.3, 5.00),
    (2.0, 7.50),
    (3.0, pytest.approx(3.25 * 3.0, abs=0.01)),
    (8.0, pytest.approx(2.60 * 8.0, abs=0.01)),
    (15.0, pytest.approx(2.25 * 15.0, abs=0.01)),
    (30.0, pytest.approx(2.10 * 30.0, abs=0.01))
])
def test_poland_air_price(weight, expected):
    result = MeestDeliveryService.get_price("Poland", "air", "courier", weight)
    assert result == expected


def test_unsupported_country():
    with pytest.raises(ValueError):
        MeestDeliveryService.get_price("France", "air", "courier", 2.0)


def test_unsupported_method():
    with pytest.raises(ValueError):
        MeestDeliveryService.get_price("US", "sea", "courier", 2.0)
