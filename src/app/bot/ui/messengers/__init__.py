# ✉️ app/bot/ui/messengers/__init__.py
"""
✉️ __init__.py — Публічний API підпакета *ui.messengers* для відправки блоків у Telegram.

🔹 Експортує зручні фасади-месенджери:
    • `ProductMessenger` — формування та відправка картки товару
    • `SizeChartMessenger` — відправка таблиць розмірів
    • `AvailabilityMessenger` — звіти про наявність/розміри

Використання (зовнішнє API):
    from app.bot.ui.messengers import ProductMessenger, SizeChartMessenger, AvailabilityMessenger
"""

# 🧩 Внутрішні модулі проєкту
from .product_messenger import ProductMessenger						# 🛍️ Відправка карток товарів
from .size_chart_messenger import SizeChartMessenger						# 📏 Відправка таблиць розмірів
from .availability_messenger import AvailabilityMessenger					# 📦 Звіти про наявність

# ================================
# 📦 ПУБЛІЧНИЙ API ПАКЕТА
# ================================
__all__ = [
    "ProductMessenger",								# Експортувати фасад для товарів
    "SizeChartMessenger",								# Експортувати фасад для таблиць розмірів
    "AvailabilityMessenger",								# Експортувати фасад для наявності
]