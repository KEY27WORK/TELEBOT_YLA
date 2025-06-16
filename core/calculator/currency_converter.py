"""
🔄 Currency Converter Module

Отвечает за конвертацию сумм между разными валютами на основе актуальных курсов.
Отделяет ответственность курсов от калькуляторов, соблюдая SRP и DIP.
"""

from typing import Dict


class CurrencyConverter:
    """
    Класс для конвертации валют.
    """

    def __init__(self, rates: Dict[str, float]):
        """
        :param rates: Словарь с курсами валют, где ключ — валюта, значение — курс.
        """
        self.rates = rates

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Конвертация суммы из одной валюты в другую.

        :param amount: Сумма в исходной валюте.
        :param from_currency: Исходная валюта.
        :param to_currency: Целевая валюта.
        :return: Сконвертированная сумма.
        """
        if from_currency == to_currency:
            return amount

        try:
            from_rate = self.rates[from_currency.upper()]
            to_rate = self.rates[to_currency.upper()]
        except KeyError as e:
            raise ValueError(f"❌ Unsupported currency: {e.args[0]}")

        # ✅ Правильная формула: курс пересчета
        conversion_rate = from_rate / to_rate
        return amount * conversion_rate
