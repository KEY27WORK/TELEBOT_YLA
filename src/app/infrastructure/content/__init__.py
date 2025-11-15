# 🧾 app/infrastructure/content/__init__.py
"""
🧾 Контентні сервіси інфраструктури (опис товару, хештеги, заголовки).

🔹 `GenderClassifier` — визначення цільового гендера за артикулом.
🔹 `HashtagGenerator` — генерація хештегів на основі правил та AI.
🔹 `ProductContentService` — агрегує текстовий/медійний контент товару.
🔹 `ProductHeaderService` — повертає короткий заголовок та основне фото.
"""

from __future__ import annotations

# ♀️ Гендерна класифікація
from .gender_classifier import GenderClassifier

# 🔖 Генерація хештегів
from .hashtag_generator import HashtagGenerator

# 🧵 Контент товарів
from .product_content_service import ProductContentDTO, ProductContentService

# 📰 Заголовок товару
from .product_header_service import ProductHeaderDTO, ProductHeaderService

__all__ = [
    "GenderClassifier",
    "HashtagGenerator",
    "ProductContentDTO",
    "ProductContentService",
    "ProductHeaderDTO",
    "ProductHeaderService",
]
