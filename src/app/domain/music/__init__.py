# 🎵 app/domain/music/__init__.py
"""
🎵 Пакет `domain.music` публікує контракти та DTO для музичної підсистеми.

🔹 `RecommendedTrack`, `MusicRecommendationResult`, `TrackInfo` — суворо типізовані DTO.
🔹 `IMusicRecommender`, `IMusicDownloader`, `IMusicFileManager` — протоколи сервісів рекомендацій/завантаження/кешу.
"""

# 🧩 Внутрішні модулі проєкту
from .interfaces import (                                            # 🧾 Реекспорт доменних типів
    RecommendedTrack,                                                # 🎧 Структурований опис треку
    MusicRecommendationResult,                                       # 📦 Результат рекомендацій
    TrackInfo,                                                       # 🎼 Дані про завантажений трек
    IMusicRecommender,                                               # 🔎 Контракт сервісу рекомендацій
    IMusicDownloader,                                                # ⬇️ Контракт завантаження
    IMusicFileManager,                                               # 🗃️ Контракт менеджера кешу
)


# ================================
# 📤 ПУБЛІЧНИЙ API ПАКЕТА
# ================================
__all__ = [
    # DTO
    "RecommendedTrack",
    "MusicRecommendationResult",
    "TrackInfo",
    # Контракти
    "IMusicRecommender",
    "IMusicDownloader",
    "IMusicFileManager",
]
