# 🔗 app/infrastructure/url/__init__.py
"""
🔗 Пакет бренд-специфічних стратегій для парсингу та нормалізації URL.

🔹 Містить конкретні реалізації `IUrlParsingStrategy`.
🔹 Інтегрується з фасадом `UrlParserService` із пакету `shared.utils`.
🔹 Дозволяє додавати нові бренди без змін у спільному коді.
"""

from __future__ import annotations

# 🧭 YoungLA
from .youngla_strategy import YoungLAUrlStrategy

__all__ = ["YoungLAUrlStrategy"]
