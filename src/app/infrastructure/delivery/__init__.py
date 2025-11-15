# 🚚 app/infrastructure/delivery/__init__.py
"""
🚚 Інфраструктурні сервіси доставки.

🔹 `MeestDeliveryService` — розрахунок тарифів доставки Meest (вага/регіон).
"""

from __future__ import annotations

from .meest_delivery_service import MeestDeliveryService	# 🚚 Реалізація IDeliveryService для Meest

__all__ = ["MeestDeliveryService"]	# 📦 Публічний експорт пакета
