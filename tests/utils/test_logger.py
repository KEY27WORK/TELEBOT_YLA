"""
🧪 test_logger.py — unit-тести для Logger

Перевіряє:
- Створення логгера
- Додавання хендлерів
- Уникнення дублювання
- Повернення коректного логгера
"""

import logging
import os
import pytest
from utils.logger import Logger


def test_logger_creation_and_handlers():
    logger = Logger.setup_logger()

    assert isinstance(logger, logging.Logger)
    assert logger.name == "BotLogger"
    assert logger.level == logging.DEBUG

    handler_types = {type(h) for h in logger.handlers}
    assert logging.StreamHandler in handler_types
    assert logging.handlers.RotatingFileHandler in handler_types


def test_logger_not_duplicated_handlers():
    logger = Logger.setup_logger()
    count_before = len(logger.handlers)

    # Вызов еще раз — не должен добавить новые хендлеры
    logger = Logger.setup_logger()
    count_after = len(logger.handlers)

    assert count_before == count_after


def test_logger_log_directory_exists():
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
    assert os.path.exists(log_dir)
