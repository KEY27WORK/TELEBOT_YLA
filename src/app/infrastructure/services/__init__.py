# 🧰 app/infrastructure/services/__init__.py
"""
🧰 Інфраструктурні оркестратори/сервіси верхнього рівня.

🔹 `ProductProcessingService` — збирає весь контент для картки товару.
🔹 `ProcessedProductData` — DTO результату з агрегованими даними.
"""

from __future__ import annotations

from .banner_drop_service import BannerDropService                                  # 🪧 Оркестратор BannerDrop
from .collection_health import CollectionHealthSummary                            # 🩺 Звіти про здоров'я колекції
from .product_processing_service import (
    ProcessedProductData,													# 📦 DTO єдиної відповіді для бота/UI
    ProductProcessingService,												# 🧰 Оркестратор обробки товару
)

__all__ = [
    "BannerDropService",													# 🪧 Сервіс автоматизації Poster-drop
    "CollectionHealthSummary",												# 🩺 Метрики здоров'я колекції
    "ProcessedProductData",													# 📦 DTO з агрегованими даними товару
    "ProductProcessingService",											# 🧰 Оркестратор повної обробки товару
]
