# 🧬 app/infrastructure/adapters/__init__.py
"""
🧬 Інфраструктурні адаптери для узгодження інтерфейсів.

🔹 `HashtagGeneratorStringAdapter` — обгортає генератор хештегів із множиною у рядковий API.
🔹 `PriceMessageFacade` / `IPriceMessageFacade` — фасад над ціновим хендлером із єдиним методом.
"""

from __future__ import annotations

# 🏷️ Хештеги
from .hashtag_adapter import HashtagGeneratorStringAdapter

# 💸 Ціновий фасад
from .price_facade import IPriceMessageFacade, PriceMessageFacade

__all__ = [
    "HashtagGeneratorStringAdapter",
    "IPriceMessageFacade",
    "PriceMessageFacade",
]
