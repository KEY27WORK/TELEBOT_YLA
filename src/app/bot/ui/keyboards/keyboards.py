# ⌨️ app/bot/ui/keyboards/keyboards.py
"""
⌨️ Формує всі клавіатури Telegram-бота.

🔹 Будує головне меню (`ReplyKeyboardMarkup`) з основними діями
🔹 Створює інлайн-меню для керування курсами валют
🔹 Повертає меню довідки з посиланнями на FAQ, usage, support
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import (                                                     # 🤖 Telegram Bot API (stubs можуть бути відсутні)
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)  # type: ignore

# 🔠 Системні імпорти
import logging                                                             # 🧾 Логування побудови клавіатур
from typing import Optional                                                # 🧰 Nullable кеші

# 🧩 Внутрішні модулі проєкту
from app.config.setup.constants import AppConstants, CONST                 # ⚙️ Константи UI/Callback (DI + глобальні)
from app.shared.utils.logger import LOG_NAME                               # 🏷️ Ім'я кореневого логера

# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
logger = logging.getLogger(LOG_NAME)                                       # 🧾 Модульний логер


# ================================
# 🏛️ ФАБРИКА КЛАВІАТУР
# ================================
class Keyboard:
    """
    🎛️ Інкапсулює побудову всіх клавіатур бота з кешуванням.
    """

    def __init__(self, constants: AppConstants) -> None:
        self.const = constants                                             # 🧩 Зберігаємо DI-константи інтерфейсу
        self._cache_main: Optional[ReplyKeyboardMarkup] = None             # 🧠 Кеш головного меню
        self._cache_currency: Optional[InlineKeyboardMarkup] = None        # 🧠 Кеш меню валют
        self._cache_help: Optional[InlineKeyboardMarkup] = None            # 🧠 Кеш меню допомоги

    # ================================
    # 🧭 ГОЛОВНЕ МЕНЮ
    # ================================
    def build_main_menu(self) -> ReplyKeyboardMarkup:
        """
        Повертає головне меню з основними режимами бота.
        """
        if self._cache_main is not None:
            return self._cache_main                                        # 🚀 Повертаємо кешоване меню

        buttons = self.const.UI.REPLY_BUTTONS                              # 🔤 Аліас для текстових кнопок
        keyboard_rows = [                                                  # 🧱 Розкладка головного меню
            [buttons.INSERT_LINKS, buttons.MY_ORDERS],
            [buttons.COLLECTION_MODE, buttons.SIZE_CHART_MODE],
            [buttons.CURRENCY, buttons.HELP],
            [buttons.PRICE_CALC_MODE, buttons.REGION_AVAILABILITY],
            [buttons.DISABLE_MODE],
        ]

        self._cache_main = ReplyKeyboardMarkup(
            keyboard=keyboard_rows,
            resize_keyboard=True,                                          # 📱 Стиснені кнопки під екран
            one_time_keyboard=False,                                       # ♻️ Залишати клавіатуру після натискання
            input_field_placeholder=getattr(self.const.UI, "REPLY_PLACEHOLDER", None) or "",  # 📝 Плейсхолдер
        )
        logger.debug("⌨️ Згенеровано головне меню")                        # 🧾 Діагностичний лог
        return self._cache_main

    # ================================
    # 💱 МЕНЮ КУРСІВ ВАЛЮТ
    # ================================
    def build_currency_menu(self) -> InlineKeyboardMarkup:
        """
        Повертає інлайн-меню для відображення/редагування курсів валют.
        """
        if self._cache_currency is not None:
            return self._cache_currency                                    # 🚀 Використовуємо кешовану версію

        ui = self.const.UI.INLINE_BUTTONS                                  # 🔤 Тексти кнопок
        cb = self.const.CALLBACKS                                          # 🧲 Будівники callback_data

        keyboard = [
            [
                InlineKeyboardButton(text=ui.SHOW_RATE, callback_data=cb.CURRENCY_SHOW_RATE.build()),
            ],
            [
                InlineKeyboardButton(text=ui.SET_RATE, callback_data=cb.CURRENCY_SET_RATE.build()),
            ],
        ]
        self._cache_currency = InlineKeyboardMarkup(keyboard)
        logger.debug("💱 Згенеровано меню валют")                          # 🧾 Діагностичний лог
        return self._cache_currency

    # ================================
    # 🆘 МЕНЮ ДОПОМОГИ
    # ================================
    def build_help_menu(self) -> InlineKeyboardMarkup:
        """
        Повертає інлайн-меню довідки з переходами на FAQ/usage/support.
        """
        if self._cache_help is not None:
            return self._cache_help                                        # 🚀 Повертаємо з кешу

        ui = self.const.UI.INLINE_BUTTONS                                  # 🔤 Тексти для кнопок
        cb = self.const.CALLBACKS                                          # 🧲 Callback-дані

        keyboard = [
            [InlineKeyboardButton(text=ui.HELP_FAQ,     callback_data=cb.HELP_SHOW_FAQ.build())],
            [InlineKeyboardButton(text=ui.HELP_USAGE,   callback_data=cb.HELP_SHOW_USAGE.build())],
            [InlineKeyboardButton(text=ui.HELP_SUPPORT, callback_data=cb.HELP_SHOW_SUPPORT.build())],
        ]
        self._cache_help = InlineKeyboardMarkup(keyboard)
        logger.debug("🆘 Згенеровано меню допомоги")                       # 🧾 Діагностичний лог
        return self._cache_help

    # ================================
    # 🔁 BACKWARD-СУМІСНІ ОБГОРТКИ
    # ================================
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """
        Сумісна зі старим API обгортка для головного меню.
        """
        return Keyboard(CONST).build_main_menu()

    @staticmethod
    def currency_menu() -> InlineKeyboardMarkup:
        """
        Сумісна зі старим API обгортка для меню валют.
        """
        return Keyboard(CONST).build_currency_menu()

    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """
        Сумісна зі старим API обгортка для меню допомоги.
        """
        return Keyboard(CONST).build_help_menu()
