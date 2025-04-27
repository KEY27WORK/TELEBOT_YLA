"""
🧪 test_ocr_service.py — unit-тести для OCRService

Перевіряє:
- Успішне OCR-розпізнавання з mock-відповіддю
- Обробку JSONDecodeError
- Обробку OpenAIError
- Чищення JSON-тексту з markdown
"""

import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from size_chart.ocr_service import OCRService
from openai import OpenAIError



@patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
@patch("openai.OpenAI")
def test_ocr_recognize_success(mock_openai_class, mock_file):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "```json\n{\"key\": \"value\"}\n```"
    mock_client.chat.completions.create.return_value = mock_response

    ocr = OCRService()
    result = ocr.recognize("dummy/image.png", "unique-size-chart")

    assert result == {"key": "value"}


@patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
@patch("openai.OpenAI")
def test_ocr_recognize_invalid_json(mock_openai_class, mock_file):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "```json\nNOT A JSON\n```"
    mock_client.chat.completions.create.return_value = mock_response

    ocr = OCRService()
    result = ocr.recognize("dummy/image.png", "unique-size-chart")

    assert result is None


@patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
@patch("openai.OpenAI")
def test_ocr_recognize_openai_error(mock_openai_class, mock_file):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = OpenAIError("OpenAI fail")


    ocr = OCRService()
    result = ocr.recognize("dummy/image.png", "unique-size-chart")

    assert result is None


def test_clean_json_text():
    raw = "```json\n{\"a\": 1}\n```"
    clean = OCRService._clean_json_text(raw)
    assert clean == '{"a": 1}'
