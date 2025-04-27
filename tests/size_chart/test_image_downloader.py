"""
🧪 test_image_downloader.py — unit-тести для ImageDownloader

Перевіряє:
- Успішне завантаження
- Обробку порожнього URL
- Обробку виключень при requests.get
"""

import pytest
import requests
from unittest.mock import patch, mock_open, MagicMock
from size_chart.image_downloader import ImageDownloader


@patch("size_chart.image_downloader.requests.get")
def test_download_success(mock_get):
    mock_response = MagicMock()
    mock_response.iter_content = lambda chunk_size: [b"data"]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    downloader = ImageDownloader("mock_image.png")
    with patch("builtins.open", mock_open()):
        result = downloader.download("https://example.com/image.png")

    assert result == "mock_image.png"
    mock_get.assert_called_once_with("https://example.com/image.png", stream=True)


def test_download_empty_url():
    downloader = ImageDownloader("test.png")
    result = downloader.download("")
    assert result is None


@patch("size_chart.image_downloader.requests.get", side_effect=requests.RequestException("Network Error"))
def test_download_request_exception(mock_get):
    downloader = ImageDownloader("error.png")
    result = downloader.download("https://invalid.url")
    assert result is None
