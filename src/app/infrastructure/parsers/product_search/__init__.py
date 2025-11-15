# 🔎 app/infrastructure/parsers/product_search/__init__.py
"""
🔎 Парсери результатів пошуку YoungLA.

🔹 `ProductSearchResolver` — витягує посилання товарів зі сторінки пошуку.
"""

from __future__ import annotations

from .search_resolver import ProductSearchResolver	# 🔍 Основний резолвер UI-пошуку

__all__ = ["ProductSearchResolver"]	# 📦 Публічний експорт search-резолвера
