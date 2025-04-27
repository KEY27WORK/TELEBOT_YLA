"""
📦 bot.content — модуль генерації текстового контенту.

Містить:
- `TranslatorService` — переклад, генерація слоганів, оцінка ваги.
- `HashtagGenerator` — створення AI-хештегів для постів.

Використовується в:
- `ProductHandler` — для генерації опису товарів.
- `CollectionHandler` — опосередковано через ProductHandler.
"""

from .translator import TranslatorService
from .hashtag_generator import HashtagGenerator

__all__ = [
    "TranslatorService",
    "HashtagGenerator"
]
