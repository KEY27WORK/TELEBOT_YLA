# 💱 app/bot/commands/currency_feature.py
"""
💱 currency_feature.py — Модуль фічі для команд, пов'язаних з валютою.

🔹 Реалізує логіку для команд `/rate`, `/set_rate` та відповідних inline-кнопок.
🔹 Реєструє свої обробники команд та callback'ів.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update                                              # 📩 Оновлення від Telegram
from telegram.ext import CallbackContext, Application, CommandHandler   # 🤖 Контекст і хендлери

# 🔠 Системні імпорти
import logging                                                           # 🧾 Логування
from typing import Dict

# 🧩 Внутрішні модулі проєкту
from app.bot.commands.base import BaseFeature, CallbackHandlerType          # 🔧 Базовий клас фіч
from app.infrastructure.currency.currency_manager import CurrencyManager    # 💱 Менеджер валют
from app.errors.error_handler import error_handler                          # 🚨 Декоратор обробки помилок
from app.shared.utils.logger import LOG_NAME                                # 📛 Імʼя логера
from app.bot.services.callback_registry import CallbackRegistry             # 🧷 Реєстрація callback'ів
from app.bot.ui import static_messages as msg                               # 💬 Статичні повідомлення

logger = logging.getLogger(LOG_NAME)                                        # ✅ Ініціалізація логера


# ================================
# ✨ ФІЧА РОБОТИ З ВАЛЮТОЮ
# ================================
class CurrencyFeature(BaseFeature):
    """
    💱 Інкапсулює логіку, пов'язану з курсами валют:
    - Команди /rate та /set_rate
    - Inline-кнопки через callback'и
    """

    def __init__(self, currency_manager: CurrencyManager, registry: CallbackRegistry):
        """
        ⚙️ Ініціалізація фічі з усіма залежностями.
        """
        self.currency_manager = currency_manager                            # 💱 Сервіс, який керує валютами
        self.registry = registry                                        # 🧷 Реєстр callback'ів (інʼєкція)
        self.registry.register(self)                                    # 🔗 Автоматична реєстрація callback-обробників

    def register_handlers(self, application: Application):
        """
        🧾 Реєструє обробники для команд /rate та /set_rate.
        ✅ (ВИПРАВЛЕНО) Назва параметра 'app' змінена на 'application' для відповідності базовому класу.
        """
        application.add_handler(CommandHandler("rate", self.show_current_rate))             # 📊 Показ поточних курсів
        application.add_handler(CommandHandler("set_rate", self.set_custom_rate))           # ✍️ Задати курс вручну

    def get_callback_handlers(self) -> Dict[str, CallbackHandlerType]:
        """
        🔗 Реєструє callback-обробники для inline-кнопок (із простором імен).
        """
        return {
            "currency:show_rate": self.show_current_rate,                   # 📲 Callback для показу курсу
            "currency:set_rate": self.prompt_set_rate,                  # ⚙️ Callback для підказки встановлення
        }

    @error_handler
    async def show_current_rate(self, update: Update, context: CallbackContext):
        """
        📊 Показує поточні курси валют з урахуванням маржі.
        """
        await self.currency_manager.update_all_rates()                      # 🔁 Оновлюємо курси через API
        all_rates = self.currency_manager.get_all_rates()                   # 💱 Отримуємо всі актуальні курси
        logger.info("Показано актуальні курси валют.")

        text_lines = ["<b>📊 Поточні курси валют (з маржею 0.5 uah):</b>"]
        for code, rate in all_rates.items():
            text_lines.append(f"{code} → UAH: <b>{rate:.2f} грн</b>")           # 💵 Форматування кожного рядка
        text_lines.append("\n👉 Задати вручну: /set_rate USD 42.5")
        text = "\n".join(text_lines)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML")  # 🔄 Оновлюємо повідомлення (inline)
        elif update.message:
            await update.message.reply_text(text, parse_mode="HTML")            # 📩 Відповідь на команду

    @error_handler
    async def set_custom_rate(self, update: Update, context: CallbackContext):
        """
        ✍️ Встановлює курс вручну за командою: /set_rate USD 42.5
        """
        if not update.message or not context.args or len(context.args) < 2:
            if update.message:
                await update.message.reply_text("❌ Неправильний формат. Приклад: /set_rate USD 42.5")
            return

        try:
            currency = context.args[0].upper()                          # 💱 Валюта (наприклад, USD)
            new_rate = float(context.args[1].replace(',', '.'))             # 🔢 Значення курсу

            await self.currency_manager.set_rate_manually(currency, new_rate)       # ✅ Зберігаємо вручну введений курс
            if update.effective_user:
                logger.info(f"Користувач {update.effective_user.id} встановив курс {currency} на {new_rate}")

            await update.message.reply_text(
                f"✅ Курс <b>{currency}</b> встановлено на {new_rate} грн",
                parse_mode="HTML"
            )
        except (ValueError, IndexError):
            if update.effective_user:
                logger.warning(f"Користувач {update.effective_user.id} ввів неправильну команду set_rate.")
            if update.message:
                await update.message.reply_text("❌ Неправильний формат. Приклад: /set_rate USD 42.5")

    async def prompt_set_rate(self, update: Update, context: CallbackContext):
        """
        💬 Надсилає підказку для встановлення курсу (викликається кнопкою).
        """
        if update.callback_query:
            await update.callback_query.edit_message_text(msg.CURRENCY_SET_RATE_PROMPT) # 📬 Виводимо повідомлення з підказкою
