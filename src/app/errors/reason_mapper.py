# 🧭 app/errors/reason_mapper.py
"""
🧭 Мапить винятки → `ReasonCode` + контекст для тексту помилки.

🔹 Розрізняє «видимі» помилки користувача (`UserVisibleError`) і технічні.  
🔹 Інкапсулює специфіку OpenAI, httpx, Telegram.  
🔹 Повертає словник параметрів (`ctx`), який підставляється в повідомлення.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import httpx															# 🌐 HTTP-клієнт (винятки)
import openai															# 🤖 AI SDK
from telegram.error import RetryAfter, TelegramError					# 🤖 Помилки Telegram

# 🔠 Системні імпорти
import logging															# 🧾 Логування процесу мапінгу
from typing import Any, Dict, Optional, Tuple							# 📐 Типи для повернення

# 🧩 Внутрішні модулі проєкту
from app.bot.ui import static_messages as msg							# noqa: F401	# 💬 Можливі константи (залишено для майбутніх ctx)
from app.errors.custom_errors import (									# ⚠️ Старі користувацькі помилки
    NetworkRequestError,
    ParsingError,
    UserVisibleError,
)
from .reason_codes import ReasonCode									# 🧮 Перелік причин


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger("app.errors.reason_mapper")					# 🧾 Локальний логер


# ================================
# 🧭 ОСНОВНИЙ МАПЕР
# ================================
def map_error_to_reason(exc: Exception) -> Tuple[ReasonCode, Dict[str, Any]]:
    """
    Повертає (reason_code, ctx) — ctx підставляється у текст (наприклад, {status_code}).
    """
    logger.debug("🔎 map_error_to_reason start", extra={"exc_type": type(exc).__name__})

    # ===== UserVisibleError =====
    if isinstance(exc, UserVisibleError):
        return _map_user_visible(exc)

    # ===== OpenAI =====
    if isinstance(exc, openai.RateLimitError):
        logger.debug("🚦 OpenAI rate limit detected")
        return ReasonCode.AI_RATE_LIMIT, {}
    if isinstance(exc, openai.OpenAIError):
        logger.debug("🤖 OpenAI general error")
        return ReasonCode.AI_GENERAL, {}

    # ===== httpx =====
    httpx_result = _map_httpx_errors(exc)
    if httpx_result:
        return httpx_result

    # ===== Telegram =====
    if isinstance(exc, RetryAfter):
        seconds = int(getattr(exc, "retry_after", 1))
        logger.debug("⏳ Telegram retry_after=%s", seconds)
        return ReasonCode.TELEGRAM_RETRY_AFTER, {"seconds": seconds}
    if isinstance(exc, TelegramError):
        logger.debug("🤖 Telegram general error")
        return ReasonCode.TELEGRAM_GENERAL, {}

    # ===== Fallback =====
    logger.warning("❓ Unknown error mapped to INTERNAL", extra={"exc_type": type(exc).__name__})
    return ReasonCode.INTERNAL, {}


# ================================
# 🧩 ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _map_user_visible(exc: UserVisibleError) -> Tuple[ReasonCode, Dict[str, Any]]:
    """Розбирає наші `UserVisibleError` по кодах."""
    if isinstance(exc, ParsingError):
        url = getattr(exc, "url", "")									# 🔗 Можемо підставити URL
        logger.debug("📄 ParsingError mapped", extra={"url": url})
        return ReasonCode.PARSE_FAILED, {"url": url}
    if isinstance(exc, NetworkRequestError):
        if exc.retry_after_s:
            seconds = int(exc.retry_after_s)
            logger.debug("🌐 Network retry_after detected", extra={"seconds": seconds})
            return ReasonCode.TELEGRAM_RETRY_AFTER, {"seconds": seconds}
        if exc.status_code:
            logger.debug("🌐 Network HTTP status", extra={"status_code": exc.status_code})
            return ReasonCode.HTTP_STATUS, {"status_code": exc.status_code}
        logger.debug("🌐 Network connection issue")
        return ReasonCode.HTTP_CONNECTION, {}
    logger.debug("ℹ️ Generic UserVisibleError mapped to INTERNAL")
    return ReasonCode.INTERNAL, {}


def _map_httpx_errors(exc: Exception) -> Optional[Tuple[ReasonCode, Dict[str, Any]]]:
    """Повертає ReasonCode для httpx-винятків або None."""
    if isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout)):
        logger.debug("🌐 HTTP timeout")
        return ReasonCode.HTTP_TIMEOUT, {}
    if isinstance(exc, httpx.ConnectError):
        logger.debug("🌐 HTTP connection error")
        return ReasonCode.HTTP_CONNECTION, {}
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = None
        try:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
        except Exception:
            logger.debug("⚠️ Failed to extract status_code from HTTPStatusError", exc_info=True)
        logger.debug("🌐 HTTP status error", extra={"status_code": status_code})
        return ReasonCode.HTTP_STATUS, {"status_code": status_code}
    return None


__all__ = ["map_error_to_reason"]										# 📤 Публічний API
