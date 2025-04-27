"""
🧪 test_webdriver_errors.py — unit-тести для обробника помилок WebDriver.

Перевіряє:
- TimeoutException → логування з ⌛
- NoSuchElementException → логування з 🔍
- WebDriverException → логування з ❌
- Інші помилки → логування з 🔥
"""

import pytest
from unittest.mock import patch
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from errors.webdriver_errors import handle_webdriver_error


@patch("errors.webdriver_errors.logging.warning")
def test_handle_timeout_exception_logs_warning(mock_log):
    error = TimeoutException("Сторінка зависла")
    handle_webdriver_error(error)
    mock_log.assert_called_once()
    assert "⌛" in mock_log.call_args[0][0]


@patch("errors.webdriver_errors.logging.warning")
def test_handle_no_such_element_exception_logs_warning(mock_log):
    error = NoSuchElementException("Елемент не знайдено")
    handle_webdriver_error(error)
    mock_log.assert_called_once()
    assert "🔍" in mock_log.call_args[0][0]


@patch("errors.webdriver_errors.logging.error")
def test_handle_webdriver_exception_logs_error(mock_log):
    error = WebDriverException("Загальна помилка")
    handle_webdriver_error(error)
    mock_log.assert_called_once()
    assert "❌" in mock_log.call_args[0][0]


@patch("errors.webdriver_errors.logging.critical")
def test_handle_unknown_exception_logs_critical(mock_log):
    error = Exception("Невідомий виняток")
    handle_webdriver_error(error)
    mock_log.assert_called_once()
    assert "🔥" in mock_log.call_args[0][0]
