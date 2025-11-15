# 💱 app/domain/currency/__init__.py
"""
💱 Пакет `domain.currency` публікує контракти та DTO для валютних операцій.

🔹 `interfaces.py` містить `CurrencyCode`, `Money`, виняток `CurrencyRateNotFoundError` та протоколи
    `ICurrencyConverter` (legacy), `IMoneyConverter` (Decimal API) і `ICurrencyRatesProvider`.
"""

# 🧩 Внутрішні модулі проєкту
from .interfaces import (
    CurrencyCode,                # 🔤 Типобезпечний ISO-4217 код валюти
    Money,                       # 💵 DTO для сум на базі Decimal
    CurrencyRateNotFoundError,   # 🚫 Виняток, якщо курс відсутній
    ICurrencyConverter,          # 💀 Legacy float API (зберігаємо для сумісності)
    IMoneyConverter,             # 💵 Основний Decimal-конвертер
    ICurrencyRatesProvider,      # 📈 Контракт асинхронного провайдера курсів
)


# ================================
# 📤 ПУБЛІЧНИЙ API ПАКЕТА
# ================================
__all__ = [
    "CurrencyCode",
    "Money",
    "CurrencyRateNotFoundError",
    "ICurrencyConverter",
    "IMoneyConverter",
    "ICurrencyRatesProvider",
]
