# 📬 app/bot/commands/core_commands_feature.py
"""
📬 Реалізація базових команд `/start` та `/help`.

🔹 Реєструє командні хендлери та callback-кнопки розділу «Допомога»
🔹 Відповідає за відправку привітального повідомлення й головного меню
🔹 Інкапсулює логіку показу FAQ, інструкцій та контактів підтримки
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update                                              # 📡 Об'єкт вхідного апдейту
from telegram.ext import Application, CommandHandler                     # 🧰 Реєстрація команд у застосунку

# 🔠 Системні імпорти
import logging                                                           # 🧾 Логування подій
from typing import Dict, cast                                            # 🧰 Типізація та допоміжні касти

# 🧩 Внутрішні модулі проєкту
from app.bot.commands.base import BaseFeature                            # 🏛️ Базовий контракт фічі
from app.bot.services.callback_data_factory import CallbackData          # 🏷️ Типи callback-даних
from app.bot.services.callback_registry import CallbackRegistry          # 📚 Централізований реєстр callback-хендлерів
from app.bot.services.custom_context import CustomContext                # 🧠 Розширений контекст
from app.bot.services.types import CallbackHandlerType                   # 🔗 Сигнатура callback-хендлера
from app.bot.ui import static_messages as msg                            # 📝 Статичні тексти інтерфейсу
from app.bot.ui.keyboards.keyboards import Keyboard                      # 🎛️ Генератор клавіатур
from app.config.setup.constants import AppConstants                      # ⚙️ Константи застосунку
from app.shared.utils.logger import LOG_NAME                             # 🏷️ Ім'я кореневого логера

# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
logger = logging.getLogger(LOG_NAME)                                     # 🧾 Модульний логер


# ================================
# 🏛️ ФІЧА БАЗОВИХ КОМАНД
# ================================
class CoreCommandsFeature(BaseFeature):
    """
    ✨ Інкапсулює `/start`, `/help` та callback-кнопки розділу «Допомога».
    """

    def __init__(self, registry: CallbackRegistry, constants: AppConstants) -> None:
        self.registry = registry                                          # 🗂️ Реєстр callback-хендлерів
        self.const = constants                                            # ⚙️ Константи інтерфейсу
        self.registry.register(self)                                      # ✅ Регіструємо фічу у callback-реєстрі

    # ================================
    # 🔌 РЕЄСТРАЦІЯ КОМАНД
    # ================================
    def register_handlers(self, application: Application) -> None:
        """
        Реєструє `/start` та `/help` у Telegram Application.
        """
        commands = self.const.LOGIC.COMMANDS                              # 🧭 Простір імен команд
        application.add_handler(CommandHandler(commands.START, self.start_command))  # ➕ /start
        application.add_handler(CommandHandler(commands.HELP, self.help_command))    # ➕ /help
        logger.info("🧾 Core commands registered (start/help)")           # 🧾 Фіксуємо реєстрацію

    # ================================
    # 📚 CALLBACK-КНОПКИ
    # ================================
    def get_callback_handlers(self) -> Dict[CallbackData, CallbackHandlerType]:
        """
        Повертає мапу callback-ключів на корутини для розділу «Допомога».
        """
        callbacks = self.const.CALLBACKS                                  # 🧭 Простір імен callback-ів
        mapping = {
            callbacks.HELP_SHOW_FAQ: self.show_faq,                       # ❓ FAQ
            callbacks.HELP_SHOW_USAGE: self.show_help_usage,              # 📘 Як користуватись
            callbacks.HELP_SHOW_SUPPORT: self.show_help_support,          # 🆘 Підтримка
        }
        logger.debug("📚 Core commands callbacks prepared (%d items)", len(mapping))  # 🧾 Діагностика мапи
        return cast(Dict[CallbackData, CallbackHandlerType], mapping)     # 🔁 Приводимо до очікуваного типу

    # ================================
    # ▶️ /START
    # ================================
    async def start_command(self, update: Update, context: CustomContext) -> None:
        """
        Обробляє команду `/start`: надсилає привітання та головне меню.
        """
        user_id = getattr(update.effective_user, "id", "unknown")         # 🆔 ID користувача для логів
        logger.info("➡️ /start by user=%s", user_id)                      # 🧾 Журнал аудиту

        if update.message is None:                                        # 🚫 Немає повідомлення → відповідати нікуди
            return

        await update.message.reply_text(                                  # 📤 Привітальне повідомлення
            msg.HELP_WELCOME_SHORT,
            reply_markup=Keyboard(self.const).build_main_menu(),          # 🎛️ Головне меню (через DI-константи)
            parse_mode="HTML",
        )

    # ================================
    # ▶️ /HELP
    # ================================
    async def help_command(self, update: Update, context: CustomContext) -> None:
        """
        Обробляє команду `/help`: показує головну сторінку довідки.
        """
        user_id = getattr(update.effective_user, "id", "unknown")         # 🆔 ID користувача для логів
        logger.info("ℹ️ /help by user=%s", user_id)                       # 🧾 Журнал аудиту

        if update.message is None:                                        # 🚫 Немає повідомлення → відповідати нікуди
            return

        await update.message.reply_text(                                  # 📤 Відправляємо основний довідковий текст
            msg.HELP_MAIN_TEXT,
            parse_mode="HTML",
            reply_markup=Keyboard(self.const).build_help_menu(),          # 🎛️ Inline-меню довідки
        )

    # ================================
    # 📞 CALLBACK-КНОПКИ
    # ================================
    async def show_faq(self, update: Update, context: CustomContext) -> None:
        """
        Відображає секцію «FAQ».
        """
        if update.callback_query is None:                                 # 🚫 Немає callback'у → робити нічого
            return
        await update.callback_query.edit_message_text(msg.HELP_FAQ_TEXT)  # ✏️ Оновлюємо повідомлення

    async def show_help_usage(self, update: Update, context: CustomContext) -> None:
        """
        Відображає інструкцію користування.
        """
        if update.callback_query is None:                                 # 🚫 Немає callback'у → завершити
            return
        await update.callback_query.edit_message_text(
            msg.HELP_USAGE_TEXT,
            parse_mode=self.const.UI.DEFAULT_PARSE_MODE,                  # 🅷 Форматування з констант
        )

    async def show_help_support(self, update: Update, context: CustomContext) -> None:
        """
        Відображає контакти підтримки.
        """
        if update.callback_query is None:                                 # 🚫 Немає callback'у → завершити
            return
        await update.callback_query.edit_message_text(
            msg.HELP_SUPPORT_TEXT,
            parse_mode=self.const.UI.DEFAULT_PARSE_MODE,                  # 🅷 Форматування з констант
        )
