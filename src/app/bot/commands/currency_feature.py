# 💱 app/bot/commands/currency_feature.py
"""
💱 Обробка команд і callback-ів, пов'язаних із валютами.

🔹 Реєструє `/rate`, `/set_rate` та відповідні callback-кнопки
🔹 Виводить поточні курси й дозволяє встановлювати кастомні значення
🔹 Використовує централізований ExceptionHandler та CurrencyManager
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update                                                # ✉️ Подія від Telegram
from telegram.ext import Application, CommandHandler                       # 🤖 Реєстрація команд у застосунку

# 🔠 Системні імпорти
import logging                                                             # 🧾 Логування операцій
import re                                                                  # 🔍 Парсинг аргументів користувача
from decimal import Decimal, InvalidOperation                              # 💰 Робота з курсами
from typing import Dict, Optional, Tuple, cast                             # 🧰 Типізація для строгості контрактів

# 🧩 Внутрішні модулі проєкту
from app.bot.commands.base import BaseFeature                              # 🏛️ Базовий контракт фічі
from app.bot.services.callback_data_factory import CallbackData            # 🏷️ Типи callback-даних
from app.bot.services.callback_registry import CallbackRegistry            # 📚 Реєстр callback-обробників
from app.bot.services.custom_context import CustomContext                  # 🧠 Кастомний контекст апдейту
from app.bot.services.types import CallbackHandlerType                     # 🔗 Сигнатура callback-обробника
from app.bot.ui import static_messages as msg                              # 📝 Статичні повідомлення
from app.config.setup.constants import AppConstants                        # ⚙️ Константи застосунку
from app.errors.error_handler import make_error_handler                    # 🛡️ Обгортка для безпечного виклику
from app.errors.exception_handler_service import ExceptionHandlerService   # 🚑 Централізована обробка помилок
from app.infrastructure.currency.currency_manager import CurrencyManager   # 💱 Менеджер курсів валют
from app.shared.utils.logger import LOG_NAME                               # 🏷️ Ім'я кореневого логера

# ================================
# 🧾 ЛОГЕР ТА КОНСТАНТИ МОДУЛЯ
# ================================
logger = logging.getLogger(LOG_NAME)                                       # 🧾 Модульний логер
_RATE_PATTERN = re.compile(r"^\s*([A-Za-z]{3})\s*[:=]?\s*([\d.,]+)\s*$")   # 🔎 Шаблон для парсингу аргументів


# ================================
# 💼 ФІЧА УПРАВЛІННЯ КУРСАМИ
# ================================
class CurrencyFeature(BaseFeature):
    """
    💱 Інкапсулює логіку перегляду та встановлення курсів валют.
    """

    def __init__(
        self,
        currency_manager: CurrencyManager,
        registry: CallbackRegistry,
        constants: AppConstants,
        exception_handler: ExceptionHandlerService,
    ) -> None:
        self.currency_manager = currency_manager                            # 💱 Джерело даних про курси
        self.registry = registry                                           # 📚 Реєстр callback-ів
        self.const = constants                                             # ⚙️ Команди та UI-константи

        safe_wrapper = make_error_handler(exception_handler)               # 🛡️ Фабрика безпечних викликів
        self._safe_show_current_rate = cast(
            CallbackHandlerType,
            safe_wrapper(self.show_current_rate),
        )                                                                  # 🧰 Безпечний обробник показу курсу
        self._safe_set_custom_rate = cast(
            CallbackHandlerType,
            safe_wrapper(self.set_custom_rate),
        )                                                                  # 🧰 Безпечний обробник встановлення курсу
        self._safe_prompt_set_rate = cast(
            CallbackHandlerType,
            safe_wrapper(self.prompt_set_rate),
        )                                                                  # 🧰 Безпечний обробник підказки

        self.registry.register(self)                                       # 🔗 Публікуємо callback-и у реєстр
        logger.info("💱 CurrencyFeature initialised and registered")       # 🧾 Лог ініціалізації

    # ================================
    # 🔌 РЕЄСТРАЦІЯ КОМАНД
    # ================================
    def register_handlers(self, application: Application) -> None:
        """
        Реєструє командні обробники `/rate` та `/set_rate`.
        """
        commands = self.const.LOGIC.COMMANDS                               # 🧭 Простір імен команд
        application.add_handler(CommandHandler(commands.RATE, self._safe_show_current_rate))      # ➕ /rate
        application.add_handler(CommandHandler(commands.SET_RATE, self._safe_set_custom_rate))    # ➕ /set_rate
        logger.info("📝 Currency commands registered (/rate, /set_rate)")   # 🧾 Фіксуємо реєстрацію

    def get_callback_handlers(self) -> Dict[CallbackData, CallbackHandlerType]:
        """
        Повертає callback-хендлери для меню валют.
        """
        callbacks = self.const.CALLBACKS                                   # 🧭 Простір імен callback-ів
        mapping = {
            callbacks.CURRENCY_SHOW_RATE: self._safe_show_current_rate,    # 🔘 Кнопка «Показати курс»
            callbacks.CURRENCY_SET_RATE: self._safe_prompt_set_rate,       # 🔘 Кнопка «Змінити курс»
        }
        logger.debug("🎛️ Currency callback map prepared (%d items)", len(mapping))  # 🧾 Діагностика callback-ів
        return mapping

    # ================================
    # 💱 ПОКАЗ КУРСІВ
    # ================================
    async def show_current_rate(self, update: Update, context: CustomContext) -> None:
        """
        Відправляє користувачу поточні курси валют.
        """
        await self.currency_manager.update_all_rates_if_needed()           # 🔄 Оновлюємо кеш за потреби
        rates = self.currency_manager.get_all_rates()                      # 💹 Поточні курси (Decimal)
        lines = [f"• <b>{code}</b>: {float(rate):.2f}" for code, rate in rates.items()]  # 🧾 Форматуємо список курсів
        body = "\n".join(lines) or "❔ Курси не налаштовані."              # 🟡 Fallback, якщо курсів немає

        logger.info("📈 Currency rates shown (%d entries)", len(rates))     # 🧾 Лог відправлених курсів
        await self._safe_reply_or_edit(update, f"💱 <b>Поточні курси:</b>\n{body}")  # ✉️ Відповідь у чат

    # ================================
    # ✏️ ВСТАНОВЛЕННЯ КУРСУ
    # ================================
    async def set_custom_rate(self, update: Update, context: CustomContext) -> None:
        """
        Парсить аргументи та встановлює кастомний курс валюти.
        """
        if update.message is None:
            await self._safe_reply_or_edit(update, msg.CURRENCY_SET_RATE_INVALID_FORMAT)  # 🚫 Немає аргументів
            return

        raw_args = update.message.text or ""                               # 🧾 Повний текст команди
        parts = raw_args.split(maxsplit=1)
        if len(parts) < 2:
            await self._safe_reply_or_edit(
                update,
                msg.CURRENCY_SET_RATE_PROMPT.format(command=self.const.LOGIC.COMMANDS.SET_RATE),
            )                                                              # ℹ️ Пояснюємо формат
            logger.warning("⚠️ /set_rate called without value")
            return

        parsed = self._parse_rate_arg(parts[1])                            # 🧮 Підготовка аргументу
        if not parsed:
            await self._safe_reply_or_edit(update, msg.CURRENCY_SET_RATE_INVALID_FORMAT)  # 🚫 Неправильний формат
            logger.warning("⚠️ /set_rate invalid format raw=%r", parts[1])
            return

        code, value = parsed                                              # 🧩 Код валюти та значення
        if not (Decimal("1") <= value <= Decimal("500")):
            await self._safe_reply_or_edit(update, msg.CURRENCY_RATE_OUT_OF_RANGE)        # 🚧 Межі значення
            logger.warning("🚧 /set_rate out of range code=%s value=%s", code, value)
            return

        await self.currency_manager.set_rate_manually(code, float(value))  # 💾 Зберігаємо курс
        if update.effective_user:
            logger.info(
                "👤 user=%s встановив курс %s=%s",
                update.effective_user.id,
                code,
                value,
            )                                                              # 🧾 Аудит операції

        await self._safe_reply_or_edit(
            update,
            f"✅ Курс <b>{code}</b> встановлено на {value:.2f} грн",
        )                                                                  # 📤 Підтвердження користувачу
        logger.info("✅ Rate set manually code=%s value=%.2f", code, value)  # 🧾 Лог дії

    # ================================
    # 💬 ПІДКАЗКА ФОРМАТУ
    # ================================
    async def prompt_set_rate(self, update: Update, context: CustomContext) -> None:
        """
        Надсилає підказку, як правильно викликати команду встановлення курсу.
        """
        command_name = self.const.LOGIC.COMMANDS.SET_RATE                  # 🧭 Назва команди
        await self._safe_reply_or_edit(
            update,
            msg.CURRENCY_SET_RATE_PROMPT.format(command=command_name),
        )                                                                  # 📝 Інструкція для користувача
        logger.debug("ℹ️ Prompted user with /set_rate format")             # 🧾 Фіксуємо підказку

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    async def _safe_reply_or_edit(self, update: Update, text: str) -> None:
        """
        Безпечно редагує існуюче повідомлення або відправляє нове.
        """
        parse_mode = self.const.UI.DEFAULT_PARSE_MODE                      # 🅿️ Використовуємо єдиний parse_mode
        callback = getattr(update, "callback_query", None)                 # 🔍 Перевіряємо, чи це callback

        if callback:
            try:
                await callback.edit_message_text(text, parse_mode=parse_mode)  # ✏️ Пробуємо редагувати
            except Exception:
                logger.exception("edit_message_text failed; fallback to send_message")  # ⚠️ Лог помилки
                try:
                    if callback.message and callback.message.chat:
                        await callback.message.chat.send_message(text, parse_mode=parse_mode)  # 📤 Резервний сценарій
                except Exception:
                    logger.exception("fallback send_message failed")       # ⚠️ Зафіксували збій fallback
            finally:
                try:
                    await callback.answer()                                # ✅ Закриваємо індикатор кнопки
                except Exception:
                    logger.debug("callback_query.answer failed", exc_info=True)  # ℹ️ Не критично, але варто знати
            return

        if update.message:
            try:
                await update.message.reply_text(text, parse_mode=parse_mode)  # ✉️ Відповідаємо у чат
            except Exception:
                logger.exception("reply_text failed")                     # ⚠️ Фіксуємо у логах

    def _parse_rate_arg(self, raw: str) -> Optional[Tuple[str, Decimal]]:
        """
        Парсить рядок формату «USD 42.5», «usd=42,5», «Usd:42.5» тощо.
        """
        match = _RATE_PATTERN.match(raw)
        if match:
            code, numeric = match.groups()                                # 🧩 Зчитуємо код та числову частину
        else:
            fragments = raw.split()
            if len(fragments) != 2:
                return None                                               # 🚫 Невідомий формат
            code, numeric = fragments

        currency_code = code.upper().strip()                              # 🔤 Нормалізуємо код валюти
        normalized_numeric = numeric.replace(",", ".").strip()            # 🔁 Замінюємо кому на крапку

        try:
            value = Decimal(normalized_numeric)                           # 💰 Конвертуємо у Decimal
        except InvalidOperation:
            return None                                                   # 🚫 Неможливо перетворити у число

        return currency_code, value                                       # 📤 Повертаємо код та числове значення
