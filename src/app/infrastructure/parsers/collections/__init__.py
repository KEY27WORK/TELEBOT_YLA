# 📚 app/infrastructure/parsers/collections/__init__.py
"""
📚 Парсери сторінок колекцій YoungLA.

🔹 `UniversalCollectionParser` — INFRA-парсер, що читає JSON-LD, DOM та пагінацію.
🔹 Повертає унікальний список продуктів для подальшої обробки.
"""

from __future__ import annotations

# 🧩 Внутрішні модулі проєкту
from .universal_collection_parser import UniversalCollectionParser			# 🌐 Парсер coll-page (JSON-LD + DOM)

__all__ = [
    "UniversalCollectionParser",											# 🌐 Публічний парсер колекцій YoungLA
]
