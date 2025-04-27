"""
🧪 test_webdriver_service.py — unit-тести для WebDriverService

Перевіряє:
- Ініціалізацію драйвера
- Перезапуск і завершення
- Завантаження сторінки з обробкою помилок
"""

import pytest
from unittest.mock import patch, MagicMock
from core.webdriver.webdriver_service import WebDriverService


@patch("core.webdriver.webdriver_service.webdriver.Chrome")
def test_setup_driver_success(mock_chrome):
    service = WebDriverService()
    service.driver = None
    service.setup_driver()
    mock_chrome.assert_called_once()
    assert service.driver is not None


@patch("core.webdriver.webdriver_service.webdriver.Chrome", side_effect=Exception("fail"))
def test_setup_driver_fail(mock_chrome):
    service = WebDriverService()
    service.driver = None
    service.setup_driver()
    assert service.driver is None


def test_quit_driver():
    service = WebDriverService()
    mock_driver = MagicMock()
    service.driver = mock_driver
    service.quit_driver()
    mock_driver.quit.assert_called_once()
    assert service.driver is None


@patch.object(WebDriverService, "quit_driver")
@patch.object(WebDriverService, "setup_driver")
def test_restart_driver(mock_setup, mock_quit):
    service = WebDriverService()
    service.restart_driver()
    mock_quit.assert_called_once()
    mock_setup.assert_called_once()


def test_is_driver_alive_true():
    service = WebDriverService()
    mock_driver = MagicMock()
    mock_driver.window_handles = [1]
    service.driver = mock_driver
    assert bool(service.is_driver_alive()) is True


def test_is_driver_alive_false():
    service = WebDriverService()
    mock_driver = MagicMock()
    mock_driver.window_handles = []
    service.driver = mock_driver
    assert bool(service.is_driver_alive()) is False


@patch("core.webdriver.webdriver_service.webdriver.Chrome")
@patch("core.webdriver.webdriver_service.WebDriverWait")
def test_fetch_page_source_success(mock_wait, mock_chrome):
    mock_driver = MagicMock()
    mock_driver.page_source = "<html><body>OK</body></html>"
    mock_chrome.return_value = mock_driver
    mock_wait.return_value.until.return_value = True

    service = WebDriverService()
    service.driver = mock_driver
    page = service.fetch_page_source("https://test.com", max_retries=1)
    assert "OK" in page


@patch("core.webdriver.webdriver_service.webdriver.Chrome")
def test_fetch_page_source_fail(mock_chrome):
    mock_driver = MagicMock()
    mock_driver.get.side_effect = Exception("fail")
    mock_chrome.return_value = mock_driver

    service = WebDriverService()
    service.driver = mock_driver
    page = service.fetch_page_source("https://fail.com", max_retries=1)
    assert page is None
