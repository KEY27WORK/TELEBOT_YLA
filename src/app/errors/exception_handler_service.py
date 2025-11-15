# 🛡️ app/errors/exception_handler_service.py
"""
🛡️ Центральний сервіс обробки помилок для Telegram-бота.

🔹 Конвертує будь-які винятки в доменні `AppError`, використовуючи передані стратегії.  
🔹 Визначає, що показати користувачу (`UserVisibleError` або unified fallback).  
🔹 Логує повний контекст (user_id, код помилки, payload) і ніколи не валить хендлер.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update											# 🤖 Telegram DTO

# 🔠 Системні імпорти
import asyncio														# ⏱️ CancelledError
import logging														# 🧾 Логування кроків
from typing import Any, List, Mapping, Optional					# 📐 Типи

# 🧩 Внутрішні модулі проєкту
from app.bot.ui import static_messages as msg						# 💬 Стандартні повідомлення
from app.bot.ui.error_presenter import build_error_message			# 🧱 Формування тексту помилки
from app.shared.utils.logger import LOG_NAME						# 🏷️ Спільний неймспейс логів
from .custom_errors import AppError, UserVisibleError				# ⚠️ Доменні винятки
from .reason_mapper import map_error_to_reason						# 🗺️ Маппер причин
from .strategies import IErrorHandlingStrategy						# 🧠 Конвертери винятків


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)								# 🧾 Іменований логер модуля


# ================================
# 🧠 СЕРВІС ОБРОБКИ ПОМИЛОК
# ================================
class ExceptionHandlerService:
    """🧠 Глобальний диспетчер помилок для асинхронних Telegram-хендлерів."""

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(self, strategies: List[IErrorHandlingStrategy]) -> None:
        self._strategies = list(strategies)							# 📦 Копія списку, щоб уникнути мутацій
        logger.info("🛡️ ExceptionHandlerService init", extra={"strategies": len(self._strategies)})

    # ================================
    # 🔑 ПУБЛІЧНИЙ API
    # ================================
    async def handle(self, error: Exception, update: Optional[Update]) -> None:
        """
        Головна точка входу. Нічого не піднімає, окрім CancelledError.
        """
        if isinstance(error, asyncio.CancelledError):					# ⏹️ CancelledError передається вище
            logger.info("⏹️ CancelledError passthrough")
            raise

        domain_error = self._convert_error(error)					# 🔄 Прагнемо отримати AppError
        user_id = self._extract_user_id(update)						# 🆔 Для логів

        if isinstance(domain_error, UserVisibleError):				# 👀 Показуємо повідомлення як є
            extra = self._extract_extra(domain_error)				# 📦 payload для логів
            logger.warning(
                "⚠️ UserVisibleError for user=%s: %s",
                user_id,
                domain_error,
                extra=extra,
            )
            await self._safe_reply(update, domain_error.message)	# 💬 Відповідаємо користувачу
            return

        await self._handle_unified(error, user_id, update)			# 🌐 Фолбек: reason + next steps

    # ================================
    # 🛠️ ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _convert_error(self, error: Exception) -> Optional[AppError]:
        """🔄 Пропускає виняток через стратегії й повертає `AppError`, якщо можливо."""
        for strategy in self._strategies:							# 🔁 Перебираємо всі стратегії
            try:
                converted = strategy.handle(error)					# 🧠 Спроба конвертації
            except Exception as exc:									# noqa: BLE001
                logger.exception("🔥 Strategy failed: %r", strategy, exc_info=exc)  # 🚫 Стратегія впала — лог і далі
                continue
            if converted:
                logger.debug("🔁 Strategy converted error via %r", strategy)  # 🟢 Є результат
                return converted											# ↩️ Повертаємо AppError

        if isinstance(error, AppError):								# 🧾 Уже доменний виняток
            logger.debug("🔁 Error already AppError: %s", error)
            return error
        return None

    def _extract_user_id(self, update: Optional[Update]) -> str:
        """🆔 Витягує user_id для логів, навіть якщо update None."""
        if not update:												# 🚫 Немає update — повертаємо заглушку
            logger.debug("ℹ️ _extract_user_id: update is None")
            return "N/A"
        try:
            user = update.effective_user								# 👤 Telegram user (може бути None)
            user_id = str(user.id) if user else "N/A"
            logger.debug("🆔 _extract_user_id resolved", extra={"user_id": user_id})
            return user_id
        except Exception:
            logger.debug("⚠️ Failed to extract user_id", exc_info=True)
            return "N/A"

    def _extract_extra(self, error: UserVisibleError) -> Optional[Mapping[str, Any]]:
        """📦 Викликає `to_log_extra`, якщо він реалізований."""
        log_extra = getattr(error, "to_log_extra", None)				# 🧭 Витягуємо метод, якщо є
        if callable(log_extra):										# ✅ Тільки callable вважаємо валідним
            try:
                payload = log_extra()								# 📦 Викликаємо метод
                if isinstance(payload, Mapping):						# ☑️ Очікуємо Mapping
                    logger.debug("📦 to_log_extra payload extracted")
                    return dict(payload)								# 🧾 Створюємо копію
                logger.debug("⚠️ to_log_extra returned non-mapping")
            except Exception:
                logger.debug("⚠️ to_log_extra failed", exc_info=True)  # 🚫 Не ламаємо обробку
        return None

    async def _handle_unified(self, error: Exception, user_id: str, update: Optional[Update]) -> None:
        """🌐 Єдиний фолбек — мапимо код + будуємо повідомлення."""
        try:
            logger.error("🔥 Unhandled exception for user=%s", user_id, exc_info=error)
            code, ctx = map_error_to_reason(error)					# 🗺️ Отримуємо reason code
            text = build_error_message(code, ctx=ctx)				# 🧱 Формуємо відповідь
            logger.warning(
                "⚠️ Unified error shown | user=%s | code=%s | ctx=%r",
                user_id,
                getattr(code, "name", str(code)),
                ctx,
            )
            await self._safe_reply(update, text)
        except Exception:
            logger.exception("🔥 Failed to present unified error for user=%s", user_id)
            await self._safe_reply(update, msg.ERROR_CRITICAL)		# 🛟 Fallback

    async def _safe_reply(self, update: Optional[Update], text: str) -> None:
        """💬 Тихо намагається відповісти користувачу, не валячи обробник."""
        if not update:												# 🚫 Немає update — нічого відповісти
            logger.debug("ℹ️ _safe_reply: update is None")
            return

        message = getattr(update, "message", None) or getattr(update, "effective_message", None)  # 📬 Дістаємо message
        if not message:												# 🚫 Немає message — лог і вихід
            logger.debug("ℹ️ _safe_reply: no message object")
            return

        try:
            await message.reply_text(text)							# 📤 Надсилаємо текст
        except Exception as send_err:
            logger.warning("⚠️ Failed to send error message: %s", send_err)


__all__ = ["ExceptionHandlerService"]								# 📤 Публічний API
