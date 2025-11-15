# 📋 app/bot/commands/main_menu_feature.py
"""
📋 Фіча головного меню (Reply‑кнопки).

Призначення:
- Обробляє натискання кнопок головного меню (ReplyKeyboardMarkup).
- Вмикає/вимикає режими роботи та показує інлайн‑меню (валюти/довідка).

Інтеграція:
- `Container` створює `MainMenuFeature(constants=CONST)` і експонує як
  `container.main_menu_feature` (та legacy‑аліас `menu_handler`).
- `BotRegistrar` реєструє глобальний MessageHandler із regex‑патерном,
  який делегує на `MainMenuFeature.handle_menu`.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update                                              # ✉️ Подія від Telegram (type-ignore для stubs)

# 🔠 Системні імпорти
import logging                                                           # 🧾 Логування операцій

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext                # 🧠 Розширений контекст бота
from app.bot.ui import static_messages as msg                            # 📝 Статичні повідомлення
from app.bot.ui.keyboards.keyboards import Keyboard                      # 🎛️ Побудова клавіатур
from app.config.setup.constants import AppConstants                      # ⚙️ Константи застосунку
from app.shared.utils.logger import LOG_NAME                             # 🏷️ Кореневий логер


logger = logging.getLogger(LOG_NAME)                                     # 🧾 Модульний логер


class MainMenuFeature:
    """Обробляє текстові кнопки головного меню та перемикає режими."""

    def __init__(self, *, constants: AppConstants) -> None:
        self.const = constants                                            # 📦 Константи з UI/LOGIC/COMMANDS
        logger.info("📋 MainMenuFeature initialised with constants=%s", type(constants).__name__)  # 🧾 Діагностика DI

    async def handle_menu(self, update: Update, context: CustomContext) -> None:
        """Єдина точка обробки натискань на кнопки головного меню."""
        if not update.message:                                           # 🚫 Немає тексту, нічого обробляти
            logger.debug("📭 Skip main menu: update without message")
            return

        user_id = getattr(update.effective_user, "id", "unknown")         # 🆔 Ідентифікатор користувача
        text = (update.message.text or "").strip()                        # 📝 Текст кнопки
        buttons = self.const.UI.REPLY_BUTTONS                             # 🎛️ Набір кнопок
        modes = self.const.LOGIC.MODES                                    # 🧭 Режими роботи
        parse_mode = getattr(self.const.UI, "DEFAULT_PARSE_MODE", None)   # ✍️ Форматування відповіді

        logger.info("🕹️ MainMenu click user=%s text=%r", user_id, text)

        # 🧭 Маршрут за назвою кнопки
        if text == buttons.INSERT_LINKS:
            context.mode = modes.PRODUCT                                  # 🛒 Вмикаємо режим товарів
            logger.info("🛒 PRODUCT mode enabled for user=%s", user_id)
            await update.message.reply_text(
                msg.MENU_MODE_PRODUCT_ENABLED,
                parse_mode=parse_mode,
                reply_markup=Keyboard(self.const).build_main_menu(),
            )
            return

        if text == buttons.MY_ORDERS:
            logger.info("📦 MY_ORDERS requested by user=%s", user_id)
            await update.message.reply_text(msg.MENU_MY_ORDERS_EMPTY, parse_mode=parse_mode)
            return

        if text == buttons.COLLECTION_MODE:
            context.mode = modes.COLLECTION                               # 🧺 Режим колекцій
            logger.info("🧺 COLLECTION mode enabled for user=%s", user_id)
            await update.message.reply_text(msg.MENU_MODE_COLLECTION_ENABLED, parse_mode=parse_mode)
            return

        if text == buttons.SIZE_CHART_MODE:
            context.mode = modes.SIZE_CHART                               # 📏 Пошук таблиць
            logger.info("📏 SIZE_CHART mode enabled for user=%s", user_id)
            await update.message.reply_text(msg.MENU_MODE_SIZE_CHART_ENABLED, parse_mode=parse_mode)
            return

        if text == buttons.CURRENCY:
            logger.info("💱 Currency menu requested by user=%s", user_id)
            await update.message.reply_text(
                msg.MENU_CURRENCY_PROMPT,
                parse_mode=parse_mode,
                reply_markup=Keyboard(self.const).build_currency_menu(),
            )
            return

        if text == buttons.HELP:
            logger.info("🆘 Help menu requested by user=%s", user_id)
            await update.message.reply_text(
                msg.MENU_HELP_PROMPT,
                parse_mode=parse_mode,
                reply_markup=Keyboard(self.const).build_help_menu(),
            )
            return

        if text == buttons.PRICE_CALC_MODE:
            context.mode = modes.PRICE_CALCULATION                       # 🧮 Режим калькулятора
            logger.info("🧮 PRICE_CALC mode enabled for user=%s", user_id)
            await update.message.reply_text(msg.MENU_MODE_PRICE_CALC_ENABLED, parse_mode=parse_mode)
            return

        if text == buttons.REGION_AVAILABILITY:
            context.mode = modes.REGION_AVAILABILITY                     # 🌍 Перевірка наявності
            logger.info("🌍 REGION_AVAILABILITY mode enabled for user=%s", user_id)
            await update.message.reply_text(msg.MENU_MODE_AVAILABILITY_ENABLED, parse_mode=parse_mode)
            return

        if text == buttons.DISABLE_MODE:
            context.mode = None                                           # 🔕 Скидаємо режими
            context.url = None                                            # 🧹 Чистимо останній URL
            logger.info("🛑 All modes disabled for user=%s", user_id)
            await update.message.reply_text(
                msg.MENU_ALL_MODES_DISABLED,
                parse_mode=parse_mode,
                reply_markup=Keyboard(self.const).build_main_menu(),
            )
            return

        # Фолбек — незнайома кнопка (не повинно траплятися)
        logger.warning("⚠️ Unknown main-menu option text=%r user=%s", text, user_id)
        await update.message.reply_text(msg.MENU_UNKNOWN_OPTION, parse_mode=parse_mode)  # 📣 Сповіщаємо користувача


__all__ = ["MainMenuFeature"]                                             # 📤 Експортуємо фічу для зовнішнього використання
