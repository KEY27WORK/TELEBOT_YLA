# 🧾 app/config/setup/bot_registrar.py  — Модуль для реєстрації всіх обробників у додатку.
"""
🧾 bot_registrar.py — Модуль для реєстрації всіх обробників у додатку.

🔹 Клас `BotRegistrar`:
- Ініціалізується додатком (Application) та контейнером залежностей (Container).
- Реєструє всі обробники команд з модулів "фіч".
- Реєструє глобальні обробники (меню, колбеки, посилання).
"""

# 🌐 Внешние библиотеки
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters

# 🔠 Системні імпорти
import logging 

# 🧩 Внутренние модулі проекта
from app.config.setup.container import Container                # 📦 DI-контейнер усіх залежностей
from app.config.setup import constants as const                 # 📌 Константи для побудови регулярок
from app.shared.utils.logger import LOG_NAME                    # 🧾 Логер для інфо-повідомлень

logger = logging.getLogger(LOG_NAME)


# ================================
# 🏛️ КЛАС РЕЄСТРАТОРА
# ================================
class BotRegistrar:
    """
    🔌 Реєструє всі обробники (хендлери) в Telegram Application.
    """

    def __init__(self, application: Application, container: Container):
        """
        ⚙️ Ініціалізація з додатком та контейнером залежностей.

        Args:
            application (Application): Telegram-додаток (бот)
            container (Container): Контейнер зі всіма залежностями
        """
        self.app = application
        self.container = container
    
    def register_handlers(self):
        """
        🔗 Реєструє всі обробники: спочатку з модулів фіч, потім глобальні.
        """
        
        # ✨ 1. Автоматична реєстрація всіх фіч зі списку
        logger.info("--- Починаю автоматичну реєстрацію фіч ---")
        for feature in self.container.features:
            feature.register_handlers(self.app)
            logger.info(f"✅ Фіча '{feature.__class__.__name__}' успішно зареєстрована.")
        logger.info("--- Усі фічі зареєстровано ---")

        # 🤖 2. Реєстрація глобальних обробників

        # Обробник для всіх натискань на inline-кнопки
        self.app.add_handler(CallbackQueryHandler(self.container.callback_handler.handle))
        
        # Обробник для кнопок головного меню (використовує Regex)
        menu_pattern = const.generate_menu_pattern()        # 🧮 Побудова регулярного виразу для меню
        self.app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(menu_pattern),
            self.container.menu_handler.handle_menu
        ))

        # Обробник для всіх інших текстових повідомлень (посилання, пошукові запити)
        # Він має бути останнім серед MessageHandler, щоб не перехоплювати команди меню.
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.container.link_handler.handle_link
        ))
