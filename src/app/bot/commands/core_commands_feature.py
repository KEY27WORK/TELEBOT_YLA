# 📬 app/bot/commands/core_commands_feature.py
"""
📬 core_commands_feature.py — Модуль фічі для базових команд.

🔹 Реалізує логіку для команд `/start` та `/help`.
🔹 Реєструє свої обробники команд та callback'ів для кнопок меню допомоги.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update                                                   # 📩 Оновлення з Telegram
from telegram.ext import CallbackContext, Application, CommandHandler        # ⚙️ Контекст, апка, хендлери

# 🔠 Системні імпорти
from typing import Dict, Callable, Awaitable                                 # 🧰 Типізація обробників callback'ів

# 🧩 Внутрішні модулі проєкту
from app.bot.commands.base import BaseFeature, CallbackHandlerType           # 🧱 Базовий клас фічі та тип для callback'ів
from app.bot.ui.keyboards import Keyboard                                    # 🎛️ Клавіатури для меню
from app.errors.error_handler import error_handler                           # 🛡️ Декоратор обробки помилок
from app.bot.services.callback_registry import CallbackRegistry              # 📚 Реєстрація callback-хендлерів
from app.bot.ui import static_messages as msg                                # 💬 Статичні повідомлення


# ================================
# ✨ ФІЧА БАЗОВИХ КОМАНД
# ================================
class CoreCommandsFeature(BaseFeature):
    """
    ✨ Клас, що інкапсулює логіку для обробки основних команд
    та відповідних їм inline-кнопок.
    """

    def __init__(self, registry: CallbackRegistry):
        """
        ⚙️ Ініціалізація фічі з DI реєстром для callback'ів.
        """
        self.registry = registry                                                       # 📚 Зберігаємо інʼєкцію реєстру
        self.registry.register(self)                                                   # ✅ Реєструємо цю фічу як постачальника callback'ів

    def register_handlers(self, application: Application):
        """
        🧾 Реєструє обробники для команд /start та /help.
        """
        application.add_handler(CommandHandler("start", self.start_command))          # ▶️ /start
        application.add_handler(CommandHandler("help", self.help_command))            # 🆘 /help

    def get_callback_handlers(self) -> Dict[str, CallbackHandlerType]:
        """
        🧩 Повертає словник обробників для кнопок меню допомоги.
        Використовує простір імен 'help:'.
        """
        return {
            "help:faq": self.show_faq,                                                # ❓ Часті питання
            "help:usage": self.show_help_usage,                                      # 📖 Інструкція
            "help:support": self.show_help_support,                                  # 💬 Підтримка
        }

    # ================================
    # ▶️ ОБРОБНИКИ КОМАНД
    # ================================

    @error_handler
    async def start_command(self, update: Update, context: CallbackContext):
        """
        🎉 Обробляє команду /start.
        """
        if update.message:
            await update.message.reply_text(
                "👋 Вітаю в YoungLA Ukraine Bot! Обери пункт меню 👇",
                reply_markup=Keyboard.main_menu()
            )

    @error_handler
    async def help_command(self, update: Update, context: CallbackContext):
        """
        🆘 Обробляє команду /help.
        """
        if update.message:
            help_text = (
                "<b>👋 Ласкаво просимо до YoungLA Ukraine Bot!</b>\n\n"
                "Ось що я можу зробити для тебе:\n\n"
                "🔗 <b>Посилання на товари</b>\n"
                "Надішли посилання на будь-який товар YoungLA, і я автоматично покажу інформацію...\n\n"
                "📚 <b>Посилання на колекції</b>\n"
                "Надішли посилання на колекцію, і я опрацюю усі товари з неї.\n\n"
                "🆘 Якщо щось не зрозуміло — тисни кнопки нижче!"
            )
            await update.message.reply_text(
                text=help_text,
                parse_mode="HTML",
                reply_markup=Keyboard.help_menu()
            )

    # ================================
    # 📞 ОБРОБНИКИ ДЛЯ КНОПОК
    # ================================

    async def show_faq(self, update: Update, context: CallbackContext):
        """ 📖 Обробляє натискання кнопки 'FAQ'. """
        if update.callback_query:
            await update.callback_query.edit_message_text(msg.HELP_FAQ_TEXT)

    async def show_help_usage(self, update: Update, context: CallbackContext):
        """ 🧾 Обробляє натискання кнопки 'Як користуватись?'. """
        if update.callback_query:
            await update.callback_query.edit_message_text(msg.HELP_USAGE_TEXT, parse_mode="HTML")

    async def show_help_support(self, update: Update, context: CallbackContext):
        """ 🆘 Обробляє натискання кнопки 'Підтримка'. """
        if update.callback_query:
            await update.callback_query.edit_message_text(msg.HELP_SUPPORT_TEXT, parse_mode="HTML")
