# 🎯 app/infrastructure/services/facades/__init__.py
"""
🎯 Фасади для сервісів інфраструктури.

🔹 `AvailabilityFacade` — обгортка над AvailabilityProcessingService.  
🔹 `AvailabilityResult` — DTO заголовка та тексту кольорів.  
🔹 `MusicFacade` — обгортка над MusicRecommendation.  
🔹 `MusicSuggest` — DTO для блоку музики.
"""

from __future__ import annotations

# 🧩 Внутрішні модулі проєкту
from .availability_facade import AvailabilityFacade, AvailabilityResult		# 📊 Результат наявності
from .music_facade import MusicFacade, MusicSuggest							# 🎵 Рекомендація треку

__all__ = [
    "AvailabilityFacade",													# 📊 Формує заголовок і текст наявності
    "AvailabilityResult",													# 📦 DTO (header, colors_text)
    "MusicFacade",															# 🎵 Повертає музичну рекомендацію
    "MusicSuggest",															# 📦 DTO (title, url)
]
