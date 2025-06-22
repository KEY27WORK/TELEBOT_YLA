"""
📦 Ініціалізація пакету bot.handlers

Експортує основні обробники:
- ProductHandler — для обробки товарів
- CollectionHandler — для обробки колекцій
- PriceCalculationHandler — для розрахунку ціни товару
- SizeChartHandlerBot — для обробки таблиці розмірів
- BotCommandHandler — для команди курсу валют, довідки
"""

from .product_collection_handler import ProductHandler, CollectionHandler
from .price_calculation_handler import PriceCalculationHandler
from .size_chart_handler_bot import SizeChartHandlerBot
from .bot_command_handler import BotCommandHandler 
from core.product_availability.availability_handler import AvailabilityHandler 

__all__ = [
    "ProductHandler",
    "CollectionHandler",
    "PriceCalculationHandler",
    "SizeChartHandlerBot",
    "BotCommandHandler",
    "AvailabilityHandler",
]
