""" 🧯 webdriver_errors.py — обробник помилок Selenium WebDriver у Telegram-боті YoungLA Ukraine.

🔹 Підтримує:
- TimeoutException — сторінка завантажується занадто довго
- NoSuchElementException — елемент не знайдено
- WebDriverException — загальні помилки WebDriver

📂 Розташування: errors/webdriver_errors.py

Використовує:
- logging — для логування помилок
- selenium.exceptions — стандартні виключення WebDriver
"""

# 🧱 Системні
import logging

# 🧪 Selenium
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException
)


def handle_webdriver_error(error: Exception):
    """ 🔍 Обробляє помилки Selenium WebDriver та логує відповідні повідомлення.

    :param error: Виняток, що виник під час роботи з WebDriver.
    """
    if isinstance(error, TimeoutException):
        logging.warning(f"⌛ WebDriver: перевищено час очікування. {error}")

    elif isinstance(error, NoSuchElementException):
        logging.warning(f"🔍 WebDriver: елемент не знайдено. {error}")

    elif isinstance(error, WebDriverException):
        logging.error(f"❌ WebDriver: помилка під час роботи. {error}")

    else:
        logging.critical(f"🔥 WebDriver: невідома помилка. {error}")
