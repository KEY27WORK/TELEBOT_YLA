"""
💸 Price Calculator — переработанный модуль расчета стоимости товара
- Соблюдает принципы SOLID, DRY, KISS
- Использует паттерн Стратегия для расчета разных валют
- Разделяет конвертацию валют в отдельный CurrencyConverter
"""

from abc import ABC, abstractmethod
from core.calculator.currency_converter import CurrencyConverter


def round_price(amount: float) -> float:
    """
    Безопасное округление до 2 знаков после запятой (устраняет проблемы float).
    """
    return round(amount + 1e-8, 2)


# === Абстрактный интерфейс калькулятора (Стратегия) ===

class PriceCalculatorStrategy(ABC):
    """
    Интерфейс для всех калькуляторов цен.
    """

    def __init__(self, currency_converter: CurrencyConverter):
        self.currency_converter = currency_converter

    @abstractmethod
    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        """
        Расчет конечной стоимости.
        """
        pass


# === Конкретные стратегии ===

class USDPriceCalculator(PriceCalculatorStrategy):
    """
    Калькулятор для USD (базовая формула).
    """

    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        total = (price + delivery) * (1 + commission)
        return round_price(total)


class EURPriceCalculator(PriceCalculatorStrategy):
    """
    Калькулятор для EUR.
    """

    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        total = (price + delivery) * (1 + commission)
        return round_price(total)


class GBPPriceCalculator(PriceCalculatorStrategy):
    """
    Калькулятор для GBP.
    """

    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        total = (price + delivery) * (1 + commission)
        return round_price(total)


# === Фабрика для получения нужного калькулятора ===

class PriceCalculatorFactory:
    """
    Фабрика для выбора нужного калькулятора в зависимости от валюты.
    """

    def __init__(self, currency_converter: CurrencyConverter):
        self.currency_converter = currency_converter
        self.strategies = {
            "USD": USDPriceCalculator(self.currency_converter),
            "EUR": EURPriceCalculator(self.currency_converter),
            "GBP": GBPPriceCalculator(self.currency_converter),
        }

    def get_calculator(self, currency: str) -> PriceCalculatorStrategy:
        """
        Получение нужного калькулятора.
        """
        if currency not in self.strategies:
            raise ValueError(f"❌ Unsupported currency: {currency}")
        return self.strategies[currency]
