"""
💱 currency_converter.py — Сервіс для конвертації валют.

🔹 Основний функціонал:
- Конвертація сум між валютами на основі поточних курсів
- Централізує логіку валютних операцій для калькуляторів

✅ Дотримання SRP (Single Responsibility Principle)
✅ Відокремлення курсової логіки від бізнес-розрахунків
"""

# 📚 Імпорти
from typing import Dict


class CurrencyConverter:
    """🔄 Головний клас для конвертації валют."""

    def __init__(self, rates: Dict[str, float]):
        """
        📥 Ініціалізація конвертера з курсами.

        :param rates: Курси валют, де ключ — код валюти, значення — курс.
                      Наприклад: {"USD": 1.0, "EUR": 1.08, "UAH": 40.0, ...}
        """
        self.rates = rates

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        🔁 Конвертація суми між валютами.

        :param amount: Сума для конвертації.
        :param from_currency: Валюта з якої конвертуємо (наприклад, "USD").
        :param to_currency: Валюта в яку конвертуємо (наприклад, "UAH").
        :return: Сума в цільовій валюті.
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return amount

        try:
            from_rate = self.rates[from_currency]
            to_rate = self.rates[to_currency]
        except KeyError as e:
            raise ValueError(f"❌ Непідтримувана валюта: {e.args[0]}")

        # 🔢 Формула перерахунку валюти
        conversion_rate = from_rate / to_rate
        return amount * conversion_rate
