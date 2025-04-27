"""
🧪 test_hashtag_generator.py — unit-тести для HashtagGenerator

Перевіряє:
- Витяг артикула з назви
- Генерацію хештегів за статтю
- AI-визначення типу одягу (mock)
- AI-хештеги (mock)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.content.hashtag_generator import HashtagGenerator


def test_extract_article():
    generator = HashtagGenerator()
    assert generator.extract_article("W214 Oversized Tee") == "W214"
    assert generator.extract_article("214 Oversized Tee") == "214"
    assert generator.extract_article("NoArticle") == "NoArticle"
    assert generator.extract_article("") == ""


def test_get_gender_hashtags():
    generator = HashtagGenerator()
    assert "#younglaforher" in generator.get_gender_hashtags("W214")
    assert "#одягдлячоловіків" in generator.get_gender_hashtags("M112")


@patch("bot.content.hashtag_generator.PromptService.get_clothing_type_prompt", return_value="тип одягу?")
@patch("bot.content.hashtag_generator.openai.OpenAI")

def test_extract_clothing_type(mock_openai, mock_prompt):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=" Hoodie "))
    ]

    generator = HashtagGenerator()
    clothing_type = generator.extract_clothing_type("W214 Oversized Tee")
    assert clothing_type == "hoodie"


@patch("bot.content.hashtag_generator.PromptService.get_hashtags_prompt", return_value="промпт")
@patch("bot.content.hashtag_generator.openai.OpenAI")

def test_generate_ai_hashtags(mock_openai, mock_prompt):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="#спортивний #комфорт"))
    ]

    generator = HashtagGenerator()
    hashtags = generator.generate_ai_hashtags("W214", "Опис")
    assert "#спортивний" in hashtags
    assert "#комфорт" in hashtags
