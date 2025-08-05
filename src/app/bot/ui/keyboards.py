# ⌨️ keyboards.py — Модуль для створення клавіатур Telegram-бота.
"""
⌨️ keyboards.py — Модуль для створення клавіатур Telegram-бота.

🔹 Генерує головне меню (`main_menu`).
🔹 Створює inline-меню для роботи з валютами (`currency_menu`).
🔹 Надає меню допомоги (`help_menu`).
"""

# 🌐 Зовнішні бібліотеки
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# 🧩 Внутрішні модулі проєкту
from app.config.setup import constants as const						# 📖 Імпортуємо константи для назв кнопок


# ======================================
# ⌨️ КЛАС ДЛЯ СТВОРЕННЯ КЛАВІАТУР
# ======================================

class Keyboard:
    """
    🎛️ Клас-конструктор, що інкапсулює логіку створення всіх клавіатур бота.

    Використовує статичні методи для генерації різних типів меню.
    """

    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """
        📋 Генерує головне меню бота.

        Returns:
            ReplyKeyboardMarkup: 📦 Обʼєкт основної клавіатури.
        """
        keyboard = [
            [const.BTN_INSERT_LINKS, const.BTN_MY_ORDERS],						# 🔗 Вставити посилання, мої замовлення
            [const.BTN_COLLECTION_MODE, const.BTN_SIZE_CHART_MODE],			# 🧺 Колекції, таблиці розмірів
            [const.BTN_CURRENCY, const.BTN_HELP],								# 💱 Курс валют, допомога
            [const.BTN_PRICE_CALC_MODE, const.BTN_REGION_AVAILABILITY],		# 💸 Розрахунок ціни, наявність
            [const.BTN_DISABLE_MODE]										# ❌ Вимкнути режим
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)					# 📦 Повертаємо клавіатуру з автозміною розміру

    @staticmethod
    def currency_menu() -> InlineKeyboardMarkup:
        """
        💱 Генерує меню для керування курсом валют.

        Returns:
            InlineKeyboardMarkup: 📦 Inline-клавіатура для валют.
        """
        keyboard = [
            [InlineKeyboardButton("📊 Показати курс", callback_data="currency:show_rate")],		# 🪙 Показ курсу
            [InlineKeyboardButton("✏️ Встановити курс", callback_data="currency:set_rate")]		# 🖊 Зміна курсу вручну
        ]
        return InlineKeyboardMarkup(keyboard)										# 📦 Повертаємо inline-клавіатуру

    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """
        🆘 Генерує меню допомоги.

        Returns:
            InlineKeyboardMarkup: 📦 Inline-клавіатура допомоги.
        """
        keyboard = [
            [InlineKeyboardButton("📝 FAQ", callback_data="help:faq")],						# 📖 Часті питання
            [InlineKeyboardButton("📖 Як користуватись ботом?", callback_data="help:usage")],	# 📚 Інструкція
            [InlineKeyboardButton("📞 Зв'язатися з підтримкою", callback_data="help:support")]	# 📞 Контакт
        ]
        return InlineKeyboardMarkup(keyboard)										# 📦 Повертаємо inline-клавіатуру
