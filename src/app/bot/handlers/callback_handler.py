# 🎛️ app/bot/handlers/callback_handler.py
"""
🎛️ callback_handler.py — Централізований обробник для всіх inline-кнопок.
"""

# 🌐 Telegram API
from telegram import Update                                                    # 📩 Оновлення від Telegram
from telegram.ext import ContextTypes                                          # 🧩 Контекст (callback + user)

# 🔠 Системні імпорти
import logging                                                                  # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from app.bot.services.callback_registry import CallbackRegistry                # 📚 Реєстр callback-обробників
from app.errors.error_handler import error_handler                             # 🛡️ Декоратор для обробки помилок
from app.shared.utils.logger import LOG_NAME                                     # 🧾 Назва логгера

logger = logging.getLogger(LOG_NAME)                                            # 🧾 Ініціалізуємо логер

# ================================
# 🎛️ КЛАС ОБРОБНИКА CALLBACK-КНОПОК
# ================================
class CallbackHandler:
    """
    🎛️ Клас, що обробляє всі натискання на inline-кнопки (callback_query).
    """

    def __init__(self, registry: CallbackRegistry):
        self.registry = registry												# 📚 Зберігає реєстр callback-функцій

    @error_handler
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query												# 📩 Отримуємо callback-запит
        if not query or not query.data:
            return														# 🚫 Якщо пустий — нічого не робимо

        await query.answer() 													# ✅ Підтверджуємо callback, щоб прибрати спінер

        callback_data = query.data												# 🔡 Отримуємо текст callback'у
        logger.info(f"👆 Отримано callback: {callback_data}")							# 🧾 Логуємо callback

        handler = self.registry.get_handler(callback_data)							# 📦 Отримуємо відповідний обробник
        if handler:
            await handler(update, context)										# ▶️ Викликаємо обробник
        else:
            logger.warning(f"⚠️ Обробник для callback '{callback_data}' не знайдено.")		# ⚠️ Якщо не знайдено — лог попередження
