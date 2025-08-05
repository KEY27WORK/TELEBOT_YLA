""" 🛠️ error_handler.py — універсальний декоратор для обробки помилок у Telegram-боті YoungLA Ukraine.

🔹 Підтримує:
- OpenAI API: RateLimitError, OpenAIError
- Telegram API: BadRequest, TimedOut, NetworkError, TelegramError
- Selenium WebDriver: TimeoutException, NoSuchElementException, WebDriverException
- Інші неочікувані помилки

Використовує:
- logging — для логування
- functools — для створення декоратора
"""

# 🧱 Системні
import logging
import functools

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext
from telegram.error import BadRequest, TimedOut, NetworkError, TelegramError

# 🧠 OpenAI
import openai

# 🧪 Selenium WebDriver
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)


def error_handler(func):
    """ 🧰 Декоратор для обгортання асинхронних Telegram-обробників.
    Автоматично перехоплює, логує та обробляє типові помилки.
    
    :param func: Асинхронна функція Telegram-бота
    :return: Функція з додатковим захистом від помилок
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        update: Update = args[0] if args else None
        message = getattr(update, "message", None) or getattr(update, "effective_message", None)

        try:
            return await func(*args, **kwargs)

        # === 🔹 OpenAI помилки ===
        except openai.RateLimitError:
            logging.error("❌ Недостатньо квоти OpenAI!")
            if message:
                await message.reply_text("⚠️ Помилка: недостатньо квоти OpenAI.")

        except openai.OpenAIError as e:
            logging.error(f"🔥 OpenAI error: {str(e)}")
            if message:
                await message.reply_text(f"⚠️ OpenAI: {str(e)}")

        # === 🔹 Selenium помилки ===
        except TimeoutException:
            logging.warning("⌛ WebDriver: час очікування вичерпано.")
            if message:
                await message.reply_text("⚠️ Сторінка завантажується занадто довго.")

        except NoSuchElementException:
            logging.warning("🔍 WebDriver: елемент не знайдено.")
            if message:
                await message.reply_text("⚠️ Елемент не знайдено на сторінці.")

        except WebDriverException as e:
            logging.error(f"❌ WebDriver error: {e}")
            if message:
                await message.reply_text("⚠️ Помилка WebDriver.")

        # === 🔹 Telegram помилки ===
        except BadRequest as e:
            logging.warning(f"⚠️ Telegram BadRequest: {e}")

        except TimedOut:
            logging.warning("⌛ Telegram: тайм-аут запиту.")

        except NetworkError:
            logging.warning("🌐 Telegram: мережева помилка.")

        except TelegramError as e:
            logging.error(f"❌ Telegram API error: {e}")

        # === 🔥 Критичні інші помилки ===
        except Exception as e:
            logging.exception(f"🔥 Невідома критична помилка: {e}")
            if message:
                await message.reply_text("❌ Критична помилка! Повідом адміністратора.")

    return wrapper
