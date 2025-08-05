# 🤖 app/bot/handlers/__init__.py
"""
🤖 Пакет `handlers` — глобальні та наскрізні обробники.

📌 Призначення:
– Обробляє складну логіку, яка не є частиною окремих фіч.
– Включає маршрутизацію лінків, обробку inline-кнопок, роботу з товарами.

⚠️ Публічно "піднімаємо" тільки ключові класи.
"""

# 🔗 Глобальні обробники
from .callback_handler import CallbackHandler
from .link_handler import LinkHandler
from .size_chart_handler_bot import SizeChartHandlerBot

# 🛍️ Обробники товарів і колекцій
from .product.product_handler import ProductHandler
from .product.collection_handler import CollectionHandler

__all__ = [
    "CallbackHandler",
    "LinkHandler",
    "SizeChartHandlerBot",
    "ProductHandler",
    "CollectionHandler",
]

