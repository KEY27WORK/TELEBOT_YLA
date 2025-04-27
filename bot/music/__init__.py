"""
📦 Ініціалізація пакету bot.music

Експортує:
- MusicSender — клас для відправки музики в Telegram
- MusicRecommendation — підбір музики через GPT
- MusicFileManager — менеджер кешу, завантажень, парсингу
"""

from .music_sender import MusicSender
from .music_recommendation import MusicRecommendation
from .music_file_manager import MusicFileManager

__all__ = ["MusicSender", "MusicRecommendation", "MusicFileManager"]
