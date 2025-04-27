"""
🧪 test_open_ai_serv.py — unit-тести для OpenAIService

Перевіряє:
- Успішну відповідь від GPT
- Відповідь у випадку RateLimitError
- Відповідь у випадку будь-якої помилки
"""

import pytest
from unittest.mock import patch, MagicMock
from services.open_ai_serv import OpenAIService


def test_chat_completion_success():
    service = OpenAIService()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content.strip.return_value = "Test response"

    with patch.object(service.client.chat.completions, "create", return_value=mock_response) as mock_create:
        result = service.chat_completion("Hello, GPT!", temperature=0.5)

    mock_create.assert_called_once()
    assert result == "Test response"


def test_chat_completion_rate_limit_error():
    service = OpenAIService()

    with patch.object(service.client.chat.completions, "create", side_effect=Exception("RateLimitError")):
        result = service.chat_completion("Hello")
        assert result == "ERROR"


def test_chat_completion_generic_error():
    service = OpenAIService()

    with patch.object(service.client.chat.completions, "create", side_effect=Exception("Something went wrong")):
        result = service.chat_completion("Hello")
        assert result == "ERROR"
