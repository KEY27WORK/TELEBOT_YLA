""" 📬 bot_command_handler.py — обробник базових команд Telegram-бота YoungLA Ukraine.

🔹 Класи:
- `BotCommandHandler` — вивід курсу валют, довідки, ручна зміна курсу.

Використовує:
- Менеджер валют
- Клавіатури Telegram
- Помічник помилок (error_handler)
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 💱 Валюта
from core.currency.currency_manager import CurrencyManager

# 🛠️ Інше
from bot.keyboards import Keyboard
from errors.error_handler import error_handler

# 🧱 Системні
import logging

class BotCommandHandler:
    """
    🤖 Обработчик команд Telegram-бота:
    - Показ актуального курса валют
    - Ручная установка курса
    - Вывод справки по возможностям бота
    """

    def __init__(self, currency_manager: CurrencyManager):
        """
        ⚙️ Ініціалізація обробника команд.

        :param currency_manager: Менеджер валют (CurrencyManager)
        """
        self.currency_manager = currency_manager

    @error_handler
    async def show_current_rate(self, update: Update, context: CallbackContext):
        """
        📊 Показує поточні курси всіх валют з урахуванням маржі.
        """
        self.currency_manager.update_rate()  # 🔄 Оновлюємо курси з Monobank (якщо є нові)
        all_rates = self.currency_manager.get_all_rates()  # 📦 Отримуємо всі кешовані курси

        # 🧾 Формуємо текст відповіді
        text_lines = ["<b>📊 Поточні курси валют (з маржею 0.5 uah):</b>"]
        for code, rate in all_rates.items():
            text_lines.append(f"{code} → UAH: <b>{rate:.2f} грн</b>")

        text_lines.append("\n👉 Задати вручну: /set_rate USD 42.5")
        text = "\n".join(text_lines)

        # ✉️ Надсилаємо повідомлення
        await self._send_message(update, text)

    @error_handler
    async def set_custom_rate(self, update: Update, context: CallbackContext):
        """
        ✍️ Встановлює курс вручну за командою: /set_rate USD 42.5
        """
        try:
            currency = context.args[0].upper()
            new_rate = float(context.args[1].replace(',', '.'))

            self.currency_manager.set_rate_manually(currency, new_rate)
            await update.message.reply_text(f"✅ Курс <b>{currency}</b> встановлено на {new_rate} грн", parse_mode="HTML")
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Формат команди: /set_rate USD 42.5")

    @error_handler
    async def help_command(self, update: Update, context: CallbackContext):
        """
        🆘 Виводить довідку по функціоналу бота.
        """
        help_text = (
            "<b>👋 Ласкаво просимо до YoungLA Ukraine Bot!</b>\n\n"
            "Ось що я можу зробити для тебе:\n\n"
            "🔗 <b>Посилання на товари</b>\n"
            "Надішли посилання на будь-який товар YoungLA, і я автоматично покажу інформацію, ціни та характеристики.\n\n"
            "📚 <b>Посилання на колекції</b>\n"
            "Надішли посилання на колекцію, і я опрацюю усі товари з неї.\n\n"
            "📏 <b>Таблиця розмірів</b>\n"
            "Активуй режим «📏 Таблиця розмірів» з меню та надсилай посилання на товари.\n\n"
            "💱 <b>Курс валют</b>\n"
            "Переглядай актуальний курс і встановлюй власний курс вручну.\n\n"
            "📦 <b>Замовлення та кошик</b>\n"
            "Скоро тут буде інформація про твої замовлення та кошик!\n\n"
            "🆘 Якщо щось не зрозуміло — тисни кнопки нижче!"
        )

        keyboard = Keyboard.help_menu()
        await self._send_message(update, help_text, keyboard)

    # --- ⬇️ Приватні допоміжні методи ⬇️ ---

    @staticmethod
    async def _send_message(update: Update, text: str, reply_markup=None):
        """
        📬 Універсальна відправка повідомлення (message або callback).
        """
        if update.message:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
  

