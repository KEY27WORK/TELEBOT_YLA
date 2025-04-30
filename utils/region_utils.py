"""
📍 region_utils.py
Утиліти для визначення регіону та валюти на основі URL.

Використовується в парсерах товарів та колекцій:
- визначає валюту (USD / EUR / GBP)
- визначає регіон (US 🇺🇸 / EU 🇪🇺 / UK 🇬🇧)
"""

# 📦 Стандартні
import re


def get_currency_from_url(url: str) -> str:
    """
    💰 Повертає валюту на основі URL:
    - https://youngla.com → USD
    - https://eu.youngla.com → EUR
    - https://uk.youngla.com → GBP

    :param url: Посилання на товар або колекцію
    :return: Валюта (USD, EUR, GBP)
    :raises ValueError: якщо неможливо визначити валюту
    """
    if re.match(r"^https://(www\.)?youngla\.com/", url):
        return "USD"
    elif "eu.youngla.com" in url:
        return "EUR"
    elif "uk.youngla.com" in url:
        return "GBP"
    raise ValueError(f"❌ Невідомий регіон: {url}")


def get_region_from_url(url: str) -> str:
    """
    🌍 Повертає регіон з emoji на основі валюти:
    - USD → US 🇺🇸
    - EUR → EU 🇪🇺
    - GBP → UK 🇬🇧

    :param url: Посилання на товар або колекцію
    :return: Назва регіону з прапором
    """
    currency = get_currency_from_url(url)
    return {
        "USD": "US 🇺🇸",
        "EUR": "EU 🇪🇺",
        "GBP": "UK 🇬🇧"
    }[currency]
