# 🗃️ app/infrastructure/data_storage/__init__.py
"""
🗃️ Інфраструктурні сервіси зберігання даних.

🔹 `WeightDataService` — асинхронне сховище ваг (JSON-файл + in-memory кеш).
"""

from __future__ import annotations

# ⚖️ Сервіс даних про вагу
from .weight_data_service import WeightDataService

__all__ = ["WeightDataService"]
