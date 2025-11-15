# 📦 app/infrastructure/collection_processing/__init__.py
"""
📦 Інфраструктурний шар обробки колекцій товарів.

🔹 Нормалізує й валідуює URL сторінок колекцій.
🔹 Делегує парсинг фабриці парсерів і повертає список товарів.
🔹 Експортує сервіс `CollectionProcessingService` для використання в DI.
"""

from __future__ import annotations

# 🧭 Сервіс обробки колекцій
from .collection_processing_service import CollectionProcessingService

__all__ = ["CollectionProcessingService"]
