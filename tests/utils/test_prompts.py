"""
🧪 test_prompts.py — unit-тести для prompts.py

Перевіряє:
- Повернення промтів за типом
- Обробку помилок при невідомому типі
- Форматування з параметрами
"""

import pytest
from utils.prompts import get_prompt, get_size_chart_prompt


def test_get_prompt_music():
    result = get_prompt("music", title="Hoodie", description="Black oversized", image_url="http://img.com")
    assert "Hoodie" in result
    assert "Black oversized" in result
    assert "http://img.com" in result


def test_get_prompt_hashtags():
    result = get_prompt("hashtags", title="Tee", description="Soft cotton")
    assert "#️⃣" not in result  # В тексті промта немає emoji
    assert "Tee" in result


def test_get_prompt_translation_handles_none():
    result = get_prompt("translation", text=None)
    assert "Початковий текст:" in result


def test_get_prompt_invalid_type_raises():
    with pytest.raises(ValueError, match="❌ Промт 'invalid' не найден!"):
        get_prompt("invalid", text="fail")


def test_get_size_chart_prompt_unique():
    result = get_size_chart_prompt("unique-size-chart")
    assert "Розмірна Сітка" in result
    assert "JSON" in result


def test_get_size_chart_prompt_general():
    result = get_size_chart_prompt("general-size-chart")
    assert "Загальна Розмірна Сітка" in result


def test_get_size_chart_prompt_invalid_type():
    result = get_size_chart_prompt("unknown")
    assert result.startswith("❌")
