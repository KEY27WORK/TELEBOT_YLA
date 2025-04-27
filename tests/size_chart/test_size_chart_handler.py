"""
🧪 test_size_chart_handler.py — unit-тести для SizeChartHandler

Перевіряє:
- Пошук таблиці розмірів в HTML
- Завантаження та розпізнавання
- Вибір правильного генератора
"""

import pytest
from size_chart.size_chart_handler import SizeChartHandler, UniqueTableGenerator, GeneralTableGenerator
from unittest.mock import MagicMock, patch, AsyncMock


def test_find_size_chart_in_html_unique():
    html = '<img src="//cdn.youngla.com/images/SIZECHART123.jpg">'
    handler = SizeChartHandler("url", page_source=html)
    result = handler.find_size_chart_in_html(html)
    assert result == ("https://cdn.youngla.com/images/SIZECHART123.jpg", "unique-size-chart")


def test_find_size_chart_in_html_general():
    html = '<img src="//cdn.youngla.com/images/women-size-chart123.jpg">'
    handler = SizeChartHandler("url", page_source=html)
    result = handler.find_size_chart_in_html(html)
    assert result == ("https://cdn.youngla.com/images/women-size-chart123.jpg", "general-size-chart")


def test_find_size_chart_in_html_grid():
    html = '<img src="//cdn.youngla.com/images/Size_Chart_TOP_JOGGER_001.png">'
    handler = SizeChartHandler("url", page_source=html)
    result = handler.find_size_chart_in_html(html)
    assert result == ("https://cdn.youngla.com/images/Size_Chart_TOP_JOGGER_001.png", "grid-size-chart")


def test_get_generator_returns_unique():
    handler = SizeChartHandler("url")
    gen = handler._get_generator("unique-size-chart", {}, "out.png")
    assert isinstance(gen, UniqueTableGenerator)


def test_get_generator_returns_general():
    handler = SizeChartHandler("url")
    gen = handler._get_generator("general-size-chart", {}, "out.png")
    assert isinstance(gen, GeneralTableGenerator)


@patch("size_chart.size_chart_handler.SizeChartHandler.get_size_chart_image")
@patch("size_chart.size_chart_handler.ImageDownloader.download", return_value=True)
@patch("size_chart.size_chart_handler.OCRService.recognize", return_value={"Title": "test"})
@patch("size_chart.size_chart_handler.UniqueTableGenerator.generate", new_callable=AsyncMock, return_value="generated_size_chart.png")
@pytest.mark.asyncio
async def test_process_size_chart_success(mock_gen, mock_ocr, mock_download, mock_get_img):
    mock_get_img.return_value = ("https://img.png", "unique-size-chart")
    handler = SizeChartHandler("https://link.com")
    result = await handler.process_size_chart()
    assert result == "generated_size_chart.png"
