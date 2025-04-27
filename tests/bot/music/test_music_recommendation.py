"""
🧪 test_music_recommendation.py — unit-тести для MusicRecommendation

Перевіряє:
- Вдалу генерацію треків
- Обробку помилки (fallback)
- Взаємодію з OpenAIService
"""

import pytest
from unittest.mock import patch, MagicMock
from bot.music.music_recommendation import MusicRecommendation


@patch("bot.music.music_recommendation.OpenAIService")
def test_find_music_success(mock_openai_class):
    mock_service = MagicMock()
    mock_service.chat_completion.return_value = "1. Drake - God's Plan\n2. Kanye - Stronger"
    mock_openai_class.return_value = mock_service

    rec = MusicRecommendation()
    result = rec.find_music("Test Tee", "Стильна футболка для тренувань", "https://img.jpg")

    assert "Drake" in result
    mock_service.chat_completion.assert_called_once()


@patch("bot.music.music_recommendation.OpenAIService")
def test_find_music_error_fallback(mock_openai_class):
    mock_service = MagicMock()
    mock_service.chat_completion.return_value = "ERROR"
    mock_openai_class.return_value = mock_service

    rec = MusicRecommendation()
    result = rec.find_music("Fail Tee", "Щось пішло не так", "https://fail.jpg")

    assert result == "Музыка не была подобрана!"
