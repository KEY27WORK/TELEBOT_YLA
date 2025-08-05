# 📋 main_menu_feature.py — Фіча, що обробляє кнопки головного меню.
"""
📋 main_menu_feature.py — Фіча, що обробляє кнопки головного меню.

🔹 Реалізує логіку перемикання режимів бота.
🔹 Самостійно реєструє свій обробник.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update
from telegram.ext import CallbackContext, Application, MessageHandler, filters

# 🧩 Внутрішні модулі проєкту
from app.bot.commands.base import BaseFeature
from app.bot.ui import Keyboard 
from app.config.setup import constants as const
from app.errors.error_handler import error_handler
import logging											            # 🧾 Логування подій
from app.shared.utils.logger import LOG_NAME                       # ⚙️ Назва логера з проєкту

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)                               # 🧾 Логер для реєстрації подій

# ================================
# ✨ ФІЧА ГОЛОВНОГО МЕНЮ
# ================================

class MainMenuFeature(BaseFeature):
    """Клас, що інкапсулює логіку обробки кнопок головного меню."""

    def __init__(self):
        # 🗺️ Карта відповідності: кнопка -> (режим, відповідь)
        self.mode_map = {
            const.BTN_INSERT_LINKS: (const.MODE_PRODUCT, "✅ Режим вставки посилань на товари активовано."),
            const.BTN_COLLECTION_MODE: (const.MODE_COLLECTION, "✅ Режим колекцій активовано."),
            const.BTN_SIZE_CHART_MODE: (const.MODE_SIZE_CHART, "📏 Режим таблиць розмірів активовано."),
            const.BTN_REGION_AVAILABILITY: (const.MODE_REGION_AVAILABILITY, "🌍 Режим мульти-регіональної перевірки активовано."),
            const.BTN_PRICE_CALC_MODE: (const.MODE_PRICE_CALCULATION, "🧮 Режим розрахунку ціни активовано."),
        }

    def register_handlers(self, app: Application):
        """Реєструє обробник для кнопок головного меню."""
        # 👇 Викликаємо функцію з констант
        menu_pattern = const.generate_menu_pattern()
        app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(menu_pattern),
            self.handle_menu
        ))

    @error_handler
    async def handle_menu(self, update: Update, context: CallbackContext):
        """
        📥 Приймає текстову команду з меню та виконує відповідну дію.
        """
        # 💬 Отримуємо текст натиснутої кнопки
        text = update.message.text.strip()
        user_data = context.user_data

        # 🚀 Спроба обробити як команду на зміну режиму через карту
        if text in self.mode_map:
            mode, reply_text = self.mode_map[text]
            user_data["mode"] = mode
            await update.message.reply_text(reply_text)
            return

        # ⚙️ Обробка інших кнопок, що не встановлюють простий режим
        if text == const.BTN_MY_ORDERS:
            await update.message.reply_text("📦 У вас поки що немає замовлень.")
        
        elif text == const.BTN_CURRENCY:
            await update.message.reply_text(
                "💱 Виберіть дію з курсом валют:",
                reply_markup=Keyboard.currency_menu()
            )
        
        elif text == const.BTN_HELP:
            await update.message.reply_text(
                "🆘 Чим можу допомогти?",
                reply_markup=Keyboard.help_menu()
            )
        
        elif text == const.BTN_DISABLE_MODE:
            user_data["mode"] = None
            await update.message.reply_text(
                "⏹️ Усі режими вимкнено.",
                reply_markup=Keyboard.main_menu()
            )
            
        else:
            # ❔ Обробка невідомої команди
            logger.warning(f"📭 Отримана невідома команда з меню: {text}")
            await update.message.reply_text("❓ Ця опція поки що не підтримується.")