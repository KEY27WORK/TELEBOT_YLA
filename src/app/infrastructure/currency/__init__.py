# 💱 app/infrastructure/currency/__init__.py
"""
💱 Інфраструктурні сервіси для роботи з валютами.

🔹 `CurrencyConverter` — конвертація сум у потрібну валюту.
🔹 `CurrencyManager` — менеджер курсів та оновлення rate-файлів.
"""

from __future__ import annotations

# 🔁 Конвертація валют
from .currency_converter import CurrencyConverter

# 🧠 Керування курсами
from .currency_manager import CurrencyManager

__all__ = ["CurrencyConverter", "CurrencyManager"]
