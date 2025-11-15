# 🎵 app/infrastructure/music/__init__.py
"""
🎵 Інфраструктурний пакет для роботи з музичними рекомендаціями.

🔹 `MusicRecommendation` — підбір треків через AI/PromptService.
🔹 `MusicSender` — оркестратор відправки музики в Telegram.
🔹 `MusicFileManager` — файловий кеш аудіо.
🔹 `YtDownloader` — завантажувач аудіо з YouTube.
"""

from __future__ import annotations

from .music_file_manager import MusicFileManager   # 💾 Кешування файлів
from .music_recommendation import MusicRecommendation  # 🤖 Рекомендації
from .music_sender import MusicSender              # 📬 Відправка треків
from .yt_downloader import YtDownloader            # 📥 Завантаження з YouTube

__all__ = [
    "MusicFileManager",
    "MusicRecommendation",
    "MusicSender",
    "YtDownloader",
]
