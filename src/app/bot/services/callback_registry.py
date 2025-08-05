# 🗂️ app/bot/services/callback_registry.py
"""
🗂️ callback_registry.py — центральний реєстр для обробників inline-кнопок.

🔹 Клас `CallbackRegistry`:
    • Зберігає мапу callback'ів на функції-обробники
    • Використовується фічами з методом `get_callback_handlers()`
    • Виводить лог при конфліктах або успішній реєстрації
"""

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування
from typing import Dict, Callable, Awaitable, Optional              # 🧰 Типи для функцій

# 🌐 Зовнішні бібліотеки
from telegram import Update                                        # 🌍 Telegram-апдейт
from telegram.ext import CallbackContext                           # 🧩 Контекст callback'а

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME                       # ⚙️ Назва логера з проєкту
from app.bot.commands.base import CallbackHandlerType, Registrable                    # ✅ Імпортуємо протокол

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)                               # 🧾 Логер для реєстрації подій


# ================================
# 🏛️ КЛАС РЕЄСТРУ CALLBACK'ІВ
# ================================
class CallbackRegistry:
    """
    📍 Реєстр callback'ів: зберігає звʼязок між ключем та функцією-обробником.
    """

    def __init__(self):
        self._handlers: Dict[str, CallbackHandlerType] = {}                             # 🗂️ Мапа ключів на функції

    def register(self, feature_instance: Registrable):
        """
        ➕ Реєструє всі обробники, які повертає метод `get_callback_handlers()`.

        Args:
            feature_instance (Registrable): будь-який клас, що відповідає протоколу.
        """
        if not hasattr(feature_instance, "get_callback_handlers"):
            return                                                                      # ❌ Ігнор, якщо немає методу

        for key, handler in feature_instance.get_callback_handlers().items():
            if key in self._handlers:
                logger.warning(f"⚠️ Обробник для '{key}' перезаписано!")               # ⚠️ Попередження про конфлікт
            self._handlers[key] = handler
            logger.info(f"✅ Обробник для callback '{key}' зареєстровано.")            # ✅ Успішна реєстрація

    def get_handler(self, key: str) -> Optional[CallbackHandlerType]:
        """
        🔍 Повертає callback-обробник за ключем (або None, якщо не знайдено).

        Args:
            key (str): Значення поля callback_data з Telegram.

        Returns:
            Optional[CallbackHandlerType]: функція або None
        """
        return self._handlers.get(key)                                                  # 🔁 Повертає обробник або None
