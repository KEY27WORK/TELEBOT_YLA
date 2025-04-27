"""
🧪 test_prompt_service.py — unit-тести для PromptService

Перевіряє:
- Виклики get_*_prompt з правильними аргументами
- Інтеграцію з get_prompt / get_size_chart_prompt
"""

import pytest
from unittest.mock import patch
from utils.prompt_service import PromptService


@patch("utils.prompt_service.get_prompt")
def test_get_slogan_prompt(mock_get):
    PromptService.get_slogan_prompt("Tee", "Soft cotton shirt")
    mock_get.assert_called_once_with("slogan", title="Tee", description="Soft cotton shirt")


@patch("utils.prompt_service.get_prompt")
def test_get_music_prompt(mock_get):
    PromptService.get_music_prompt("Shorts", "For gym", "https://img.jpg")
    mock_get.assert_called_once_with("music", title="Shorts", description="For gym", image_url="https://img.jpg")


@patch("utils.prompt_service.get_prompt")
def test_get_translation_prompt(mock_get):
    PromptService.get_translation_prompt("High quality")
    mock_get.assert_called_once_with("translation", text="High quality")


@patch("utils.prompt_service.get_prompt")
def test_get_clothing_type_prompt(mock_get):
    PromptService.get_clothing_type_prompt("Hoodie 213")
    mock_get.assert_called_once_with("clothing_type", title="Hoodie 213")


@patch("utils.prompt_service.get_prompt")
def test_get_weight_prompt(mock_get):
    PromptService.get_weight_prompt("Jacket", "Warm and puffy", "https://image.jpg")
    mock_get.assert_called_once_with("weight", title="Jacket", description="Warm and puffy", image_url="https://image.jpg")


@patch("utils.prompt_service.get_prompt")
def test_get_hashtags_prompt(mock_get):
    PromptService.get_hashtags_prompt("Pants", "Stylish gym wear")
    mock_get.assert_called_once_with("hashtags", title="Pants", description="Stylish gym wear")


@patch("utils.prompt_service.get_size_chart_prompt")
def test_get_size_chart_prompt(mock_size_prompt):
    PromptService.get_size_chart_prompt("men's shorts")
    mock_size_prompt.assert_called_once_with("men's shorts")
