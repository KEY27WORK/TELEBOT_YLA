# 📬 app/infrastructure/availability/availability_handler.py
"""
📬 Координує user-facing частину Availability-флоу для Telegram-бота.

🔹 Валідує вхідний URL та вибирає локалізацію користувача.
🔹 Делегує побудову звіту `AvailabilityProcessingService`.
🔹 Відправляє результат через `AvailabilityMessenger`, логуючи всі кроки.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update											# 🤖 Обʼєкт оновлення Telegram
from telegram.ext import CallbackContext								# 🧠 Контекст PTB

try:																	# ⚙️ PTB v20+
    from telegram.constants import ChatAction							# 🧾 Константи дій чату
    _TYPING_ACTION: str | None = ChatAction.TYPING						# 💬 Індикатор «друкує»
except Exception:														# ⚙️ PTB v13/v12 fallback
    _TYPING_ACTION = "typing"											# 💬 Рядкове представлення

# 🔠 Системні імпорти
import logging															# 🧾 Логи обробника
from typing import Optional											# 📐 Анотації типів

# 🧩 Внутрішні модулі проєкту
from app.bot.ui.messengers.availability_messenger import AvailabilityMessenger  # 💌 Надсилання повідомлень
from app.infrastructure.availability.availability_i18n import normalize_lang, t	# 🌍 Локалізація
from app.infrastructure.availability.availability_processing_service import AvailabilityProcessingService  # 🧠 Побудова звітів
from app.shared.utils.logger import LOG_NAME							# 🏷️ Єдиний логер


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)									# 🧾 Локальний логер обробника


# ================================
# 🎯 ОБРОБНИК ПЕРЕВІРКИ НАЯВНОСТІ
# ================================
class AvailabilityHandler:
    """🎯 Валідатор URL + координація сервісів availability-флоу."""

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        processing_service: AvailabilityProcessingService,
        messenger: AvailabilityMessenger,
        *,
        default_lang: str = "uk",
        auto_detect_language: bool = True,
    ) -> None:
        self._processing_service = processing_service					# 🧠 Побудова зведених даних
        self._messenger = messenger										# 💌 Канал відправки відповіді
        self._default_lang = default_lang								# 🌍 Дефолтна локаль
        self._auto_detect_language = auto_detect_language				# 🧠 Чи використовувати language_code
        logger.info(
            "🎯 availability.handler_init",
            extra={
                "default_lang": default_lang,
                "auto_detect": auto_detect_language,
            },
        )																# 🪵 Фіксуємо параметри запуску

    # ================================
    # 📮 ПУБЛІЧНИЙ API
    # ================================
    async def handle_availability(
        self,
        update: Update,
        context: CallbackContext,
        url: str,
    ) -> None:
        """
        📮 Обробляє посилання користувача: збирає звіт і надсилає результат.

        Args:
            update: Telegram update з повідомленням користувача.
            context: PTB контекст, потрібний для send_chat_action.
            url: Посилання на товар для перевірки наявності.
        """
        message = update.effective_message								# 💬 Повідомлення користувача
        chat = update.effective_chat									# 🗣️ Контекст чату
        if not message or not chat:										# 🚫 Некоректний апдейт
            logger.warning(
                "⚠️ availability.handler.empty_context",
                extra={"update_id": getattr(update, "update_id", None)},
            )															# 🪵 Лог для моніторингу
            return														# ↩️ Нічого обробляти

        lang = self._select_language(update)							# 🌍 Визначаємо локаль
        logger.debug(
            "🧭 availability.handler.lang_selected",
            extra={"chat_id": chat.id, "lang": lang},
        )																# 🪵 Фіксуємо вибір мови

        if not url:														# 🚫 Посилання не передали
            await message.reply_text(t("empty_url", lang))				# 💬 Пояснюємо користувачу
            logger.warning(
                "⚠️ availability.url_empty",
                extra={"chat_id": chat.id},
            )															# 🪵 Лог для аналітики
            return														# ↩️ Без URL нема роботи

        await self._send_typing_indicator(context, chat.id)				# 💬 UX: показати «друкуємо»

        try:
            processed = await self._processing_service.process(url)		# 🧠 Збираємо дані
            if not processed:											# 🚫 Сервіс не зміг побудувати звіт
                await message.reply_text(t("process_failed", lang))		# 💬 Повідомляємо користувачу
                logger.info(
                    "⚠️ availability.process_failed",
                    extra={"chat_id": chat.id, "url": url},
                )														# 🪵 Звіт для моніторингу
                return													# ↩️ Перериваємо сценарій

            await self._messenger.send(update, processed)				# 💌 Відправляємо результат
            logger.info(
                "✅ availability.sent",
                extra={"chat_id": chat.id, "url": url},
            )															# 🪵 Фіксуємо успіх
        except Exception as exc:										# noqa: BLE001 # 🚨 Будь-яка помилка
            logger.exception(
                "🔥 availability.send_error",
                extra={"chat_id": chat.id, "url": url, "error": str(exc)},
            )															# 🪵 Стектрейс у логах
            await message.reply_text(t("send_failed", lang))			# 💬 Повідомляємо про збій

    # ================================
    # 🛠️ ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _select_language(self, update: Update) -> str:
        """🧭 Обирає локаль: дефолтну або з Telegram-користувача."""
        if not self._auto_detect_language:								# 🚫 Вимкнена автодетекція
            return self._default_lang									# ↩️ Використовуємо дефолт
        user = getattr(update, "effective_user", None)					# 👤 Користувач з оновлення
        lang_code = getattr(user, "language_code", None)				# 🌐 Telegram language_code
        resolved = normalize_lang(lang_code, default=self._default_lang)  # 🔄 Нормалізуємо код
        return resolved												# 📤 Віддаємо код локалі

    async def _send_typing_indicator(self, context: CallbackContext, chat_id: int) -> None:
        """💬 Показує індикатор «друкує», якщо це підтримується."""
        if not _TYPING_ACTION:											# 🚫 Падіння сумісності
            return														# ↩️ Нічого не робимо
        try:
            await context.bot.send_chat_action(						# 💬 Запускаємо індикатор
                chat_id=chat_id,
                action=_TYPING_ACTION,									# type: ignore[arg-type]
            )
            logger.debug(
                "⌨️ availability.typing_started",
                extra={"chat_id": chat_id},
            )															# 🪵 Фіксуємо показник
        except Exception as exc:										# noqa: BLE001 # 🚨 API/PTB збій
            logger.debug(
                "⚠️ availability.typing_failed",
                extra={"chat_id": chat_id, "error": str(exc)},
            )															# 🪵 Не критичний збій


__all__ = ["AvailabilityHandler"]										# 📦 Експортований клас
