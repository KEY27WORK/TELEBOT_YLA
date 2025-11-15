# 🧩 app/domain/products/__init__.py
"""
🧩 Пакет `domain.products` публікує доменні сутності, контракти та сервіси для роботи з товарами.

🔹 `entities.py` — `ProductInfo`, `Currency`, `Url` (чисті сутності продукту).
🔹 `interfaces.py` — DTO `SearchResult`, обмеження пошуку, протоколи провайдерів/пошуку/ваги/колекцій.
🔹 `dto.py` — допоміжні DTO (наприклад, `ProductHeaderDTO` для легких заголовків).
🔹 `services` — доменні сервіси (`WeightResolver`).
"""

# 🧩 Внутрішні модулі проєкту
from .entities import (                                        # 🧱 Базові сутності продуктів
    ProductInfo,
    Currency,
    Url,
)
from .dto import ProductHeaderDTO                              # 🧾 DTO заголовка товару
from .interfaces import (                                      # 📋 DTO та контракти пошуку/ваги/колекцій
    SEARCH_DEFAULT_LIMIT,
    SEARCH_MAX_LIMIT,
    SearchResult,
    IProductDataProvider,
    ICollectionDataProvider,
    ICollectionLinksProvider,
    ICollectionProcessingService,
    IProductSearchProvider,
    IWeightDataProvider,
    IWeightEstimator,
)
from .services import WeightResolver                           # ⚖️ Доменний сервіс визначення ваги


# ================================
# 📤 ПУБЛІЧНИЙ API ПАКЕТА
# ================================
__all__ = [
    # Сутності
    "ProductInfo",
    "Currency",
    "Url",
    # DTO
    "ProductHeaderDTO",
    "SearchResult",
    "SEARCH_DEFAULT_LIMIT",
    "SEARCH_MAX_LIMIT",
    # Контракти
    "IProductDataProvider",
    "ICollectionDataProvider",
    "ICollectionLinksProvider",
    "ICollectionProcessingService",
    "IProductSearchProvider",
    "IWeightDataProvider",
    "IWeightEstimator",
    # Сервіси
    "WeightResolver",
]
