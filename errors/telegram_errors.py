""" 📛 telegram_errors.py — обробник помилок Telegram API для Telegram-бота YoungLA Ukraine.

🔹 Функція `handle_telegram_error`:
- Розпізнає та логує типові помилки Telegram:
    - BadRequest
    - TimedOut
    - NetworkError
    - TelegramError (загальна)
- Логування відбувається на відповідному рівні (warning / error / critical)

Використовує:
- telegram.error — стандартні винятки Telegram API
- logging — системне логування
"""

# 🧱 Системні імпорти
import logging

# 🌐 Telegram API Exceptions
from telegram.error import TelegramError, BadRequest, TimedOut, NetworkError


def handle_telegram_error(error: Exception):
    """ 📛 Обробляє помилки Telegram API.

    :param error: Виняток, отриманий від Telegram
    """
    if isinstance(error, BadRequest):
        logging.warning(f"⚠️ Помилка BadRequest (невірний запит Telegram): {error}")

    elif isinstance(error, TimedOut):
        logging.warning(f"⌛ Помилка TimedOut (перевищено тайм-аут): {error}")

    elif isinstance(error, NetworkError):
        logging.warning(f"🌐 Помилка NetworkError (мережева помилка Telegram): {error}")

    elif isinstance(error, TelegramError):
        logging.error(f"❌ Загальна помилка Telegram API: {error}")

    else:
        logging.critical(f"🔥 Невідома помилка Telegram: {error}")
