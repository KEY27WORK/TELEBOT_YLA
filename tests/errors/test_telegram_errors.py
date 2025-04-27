"""
🧪 test_telegram_errors.py — unit-тести для handle_telegram_error

Перевіряє:
- Логування помилок BadRequest, TimedOut, NetworkError
- Логування загальної TelegramError
- Логування unknown exceptions як CRITICAL
"""

import logging
import pytest
from telegram.error import BadRequest, TimedOut, NetworkError, TelegramError
from errors.telegram_errors import handle_telegram_error


@pytest.mark.parametrize("error,expected_level", [
    (BadRequest("Bad input"), "⚠️"),
    (TimedOut("Timeout occurred"), "⌛"),
    (NetworkError("Network failed"), "🌐"),
    (TelegramError("Unknown telegram error"), "❌"),
    (Exception("Something unexpected"), "🔥")
])
def test_handle_telegram_error_logs(caplog, error, expected_level):
    with caplog.at_level(logging.DEBUG):
        handle_telegram_error(error)

    log = caplog.text
    assert expected_level in log
    assert str(error) in log
