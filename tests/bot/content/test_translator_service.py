"""
🧪 test_translator_service.py — unit-тести для TranslatorService

Перевіряє:
- Генерацію слогану (mock)
- Переклад опису з парсингом (mock)
- Оцінку ваги (mock + fallback)
"""

import pytest
from unittest.mock import patch, MagicMock
from bot.content.translator import TranslatorService


@patch("bot.content.translator.PromptService.get_slogan_prompt", return_value="prompt")
@patch("bot.content.translator.OpenAIService")
def test_generate_slogan(mock_openai, mock_prompt):
    mock_openai.return_value.chat_completion.return_value = "Слоган з AI"
    service = TranslatorService()
    result = service.generate_slogan("W214 Oversized Tee", "Зручна футболка")
    assert result == "Слоган з AI"


@patch("bot.content.translator.PromptService.get_translation_prompt", return_value="prompt")
@patch("bot.content.translator.OpenAIService")
def test_translate_text(mock_openai, mock_prompt):
    mock_response = (
        "МАТЕРІАЛ: Бавовна 100%\n"
        "ПОСАДКА: Oversized\n"
        "ОПИС: Дуже м’яка тканина\n"
        "МОДЕЛЬ: Зріст 180см, розмір M"
    )
    mock_openai.return_value.chat_completion.return_value = mock_response
    service = TranslatorService()
    result = service.translate_text("100% Cotton. Soft fabric.")
    assert result["МАТЕРІАЛ"] == "Бавовна 100%"
    assert result["ПОСАДКА"] == "Oversized"
    assert result["ОПИС"] == "Дуже м’яка тканина"
    assert result["МОДЕЛЬ"] == "Зріст 180см, розмір M"


@patch("bot.content.translator.PromptService.get_weight_prompt", return_value="prompt")
@patch("bot.content.translator.OpenAIService")
def test_get_weight_estimate_valid(mock_openai, mock_prompt):
    mock_openai.return_value.chat_completion.return_value = "0.75"
    service = TranslatorService()
    result = service.get_weight_estimate("Hoodie", "Теплий", "https://img.com")
    assert 0.1 <= result <= 5.0


@patch("bot.content.translator.PromptService.get_weight_prompt", return_value="prompt")
@patch("bot.content.translator.OpenAIService")
def test_get_weight_estimate_invalid(mock_openai, mock_prompt):
    mock_openai.return_value.chat_completion.return_value = "not a number"
    service = TranslatorService()
    result = service.get_weight_estimate("Hoodie", "Теплий", "https://img.com")
    assert result == 1.0
