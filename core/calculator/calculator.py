"""
💸 price_strategy_calculator.py — Стратегічний модуль базового розрахунку вартості.

🔹 Особливості:
- Паттерн "Стратегія" для різних валют
- Формула: (ціна + доставка) * (1 + комісія)
- Без складних логік, AI-комісій, націнок, округлень через гривню
- Використовує CurrencyConverter для конвертацій

📦 Застосування:
- Легкий, ізольований модуль для окремих цілей
- Основна бізнес-логіка залишається у ProductPriceService
"""

# 📚 Імпорти
from abc import ABC, abstractmethod
from core.calculator.currency_converter import CurrencyConverter


def round_price(amount: float) -> float:
    """
    🔄 Безпечне округлення до 2 знаків після коми (з усуненням floating-point похибок).
    """
    return round(amount + 1e-8, 2)


# === 🧩 Абстрактна стратегія калькулятора ===

class PriceCalculatorStrategy(ABC):
    """
    🧮 Абстрактний базовий інтерфейс стратегії розрахунку для кожної валюти.
    """

    def __init__(self, currency_converter: CurrencyConverter):
        self.currency_converter = currency_converter

    @abstractmethod
    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        """
        📊 Розрахунок фінальної вартості.
        """
        pass


# === 🇺🇸 USD Стратегія ===

class USDPriceCalculator(PriceCalculatorStrategy):
    """
    🇺🇸 Стратегія розрахунку для USD.

    🔹 Використовується в простих розрахунках:
    - Ціна + доставка + комісія
    """
    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        total = (price + delivery) * (1 + commission)
        return round_price(total)


# === 🇪🇺 EUR Стратегія ===

class EURPriceCalculator(PriceCalculatorStrategy):
    """
    🇪🇺 Стратегія розрахунку для EUR.

    🔹 Та сама проста формула розрахунку.
    """
    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        total = (price + delivery) * (1 + commission)
        return round_price(total)


# === 🇬🇧 GBP Стратегія ===

class GBPPriceCalculator(PriceCalculatorStrategy):
    """
    🇬🇧 Стратегія розрахунку для GBP.

    🔹 Та сама проста формула розрахунку.
    """
    def calculate_price(self, price: float, delivery: float, commission: float) -> float:
        total = (price + delivery) * (1 + commission)
        return round_price(total)


# === 🏭 Фабрика стратегій ===

class PriceCalculatorFactory:
    """
    🏗 Фабрика стратегій розрахунку за валютою.

    🔹 Забезпечує SRP, DIP — легко додати нову валюту.
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
        🔧 Отримання стратегії за валютою.
        """
        if currency not in self.strategies:
            raise ValueError(f"❌ Непідтримувана валюта: {currency}")
        return self.strategies[currency]
