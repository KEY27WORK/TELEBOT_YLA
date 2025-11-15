# 🧰 app/infrastructure/services/__init__.py
"""
🧰 Інфраструктурні оркестратори/сервіси верхнього рівня.

🔹 `ProductProcessingService` — збирає весь контент для картки товару.
🔹 `ProcessedProductData` — DTO результату з агрегованими даними.
"""

from __future__ import annotations

from .product_processing_service import (
    ProcessedProductData,													# 📦 DTO єдиної відповіді для бота/UI
    ProductProcessingService,												# 🧰 Оркестратор обробки товару
)

__all__ = [
    "ProcessedProductData",													# 📦 DTO з агрегованими даними товару
    "ProductProcessingService",											# 🧰 Оркестратор повної обробки товару
]
