# 📜 app/errors/strategies.py
"""
📜 Стратегії конвертації сторонніх винятків у доменні `AppError`.

🔹 Виносять логіку із `ExceptionHandlerService`, щоб сервіс залишався простим DI-клієнтом.  
🔹 Можна додавати нові стратегії, не змінюючи ядро.  
🔹 Забезпечують однакову поведінку для OpenAI, httpx, Telegram тощо.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import httpx															# 🌐 HTTP-клієнт (винятки)
import openai															# 🤖 OpenAI SDK
from telegram.error import RetryAfter, TelegramError					# 🤖 Telegram винятки

# 🔠 Системні імпорти
import logging															# 🧾 Логування стратегій
from typing import Optional, Protocol									# 📐 Типи

# 🧩 Внутрішні модулі проєкту
from app.bot.ui import static_messages as msg							# 💬 Повідомлення
from .custom_errors import AIError, AppError, NetworkRequestError		# ⚠️ Доменні помилки


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger("app.errors.strategies")					# 🧾 Локальний логер


# ================================
# 🧠 КОНТРАКТ СТРАТЕГІЙ
# ================================
class IErrorHandlingStrategy(Protocol):
    """🧠 Контракт, що визначає єдиний метод `handle`."""

    def handle(self, error: Exception) -> Optional[AppError]:
        """Вертає `AppError`, якщо виняток розпізнано, або None."""	# 🔁 Реалізації можуть повертати None


# ================================
# 🤖 OPENAI-СТРАТЕГІЯ
# ================================
class OpenAIErrorStrategy(IErrorHandlingStrategy):
    """🤖 Конвертує винятки OpenAI SDK у `AIError`."""

    def handle(self, error: Exception) -> Optional[AppError]:
        if isinstance(error, openai.RateLimitError):					# 🚦 Перевищено ліміт
            model = getattr(error, "model", None)						# 🧠 Може знадобитись у логах
            logger.debug("🚦 OpenAI rate limit", extra={"model": model})
            return AIError(msg.ERROR_AI_RATE_LIMIT, details=str(error), model=model)
        if isinstance(error, openai.OpenAIError):						# 🤖 Загальні помилки SDK
            model = getattr(error, "model", None)
            logger.debug("🤖 OpenAI general error", extra={"model": model})
            return AIError(msg.ERROR_AI_GENERAL, details=str(error), model=model)
        return None


# ================================
# 🌐 HTTPX-СТРАТЕГІЯ
# ================================
class HttpxErrorStrategy(IErrorHandlingStrategy):
    """🌐 Перетворює httpx-помилки на `NetworkRequestError`."""

    def handle(self, error: Exception) -> Optional[AppError]:
        if isinstance(error, (httpx.ReadTimeout, httpx.ConnectTimeout)):	# ⏱️ Таймаути запиту
            url = str(getattr(getattr(error, "request", None), "url", "N/A"))
            logger.debug("⏱️ httpx timeout", extra={"url": url})
            return NetworkRequestError(msg.ERROR_HTTP_TIMEOUT, url=url, details=str(error))

        if isinstance(error, httpx.ConnectError):						# 🌐 Не вдалося підʼєднатися
            url = str(getattr(getattr(error, "request", None), "url", "N/A"))
            logger.debug("🌐 httpx connect error", extra={"url": url})
            return NetworkRequestError(msg.ERROR_HTTP_CONNECTION, url=url, details=str(error))

        if isinstance(error, httpx.HTTPStatusError):					# 🔢 Неочікуваний статус
            url = str(getattr(getattr(error, "request", None), "url", "N/A"))
            status = getattr(getattr(error, "response", None), "status_code", None)
            logger.debug("🔢 httpx status error", extra={"url": url, "status": status})
            return NetworkRequestError(
                msg.ERROR_HTTP_STATUS.format(status_code=status),
                url=url,
                status_code=status,
                details=str(error),
            )

        return None


# ================================
# 🤖 TELEGRAM-СТРАТЕГІЯ
# ================================
class TelegramErrorStrategy(IErrorHandlingStrategy):
    """🤖 Конвертує Telegram-помилки в `NetworkRequestError`."""

    def handle(self, error: Exception) -> Optional[AppError]:
        if isinstance(error, RetryAfter):								# ⏳ Telegram просить повторити
            secs = int(getattr(error, "retry_after", 1))
            logger.debug("⏳ Telegram retry_after", extra={"seconds": secs})
            return NetworkRequestError(
                msg.ERROR_TELEGRAM_RETRY_AFTER.format(seconds=secs),
                details=str(error),
                retry_after_s=secs,
            )
        if isinstance(error, TelegramError):							# 🤖 Загальні telegram-помилки
            logger.debug("🤖 Telegram general error")
            return NetworkRequestError(msg.ERROR_TELEGRAM_GENERAL, details=str(error))
        return None


__all__ = [
    "IErrorHandlingStrategy",
    "OpenAIErrorStrategy",
    "HttpxErrorStrategy",
    "TelegramErrorStrategy",
]																		# 📤 Публічний API
