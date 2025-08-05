# 🚀 main.py — Точка входу для запуску Telegram-бота YoungLA Ukraine.

# 🌐 Внешние библиотеки
from telegram.ext import Application

# 🔠 Системные импорты
import asyncio
import logging
import sys
import os

# 🧩 Внутренние модули проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.config.config_service import ConfigService
from app.config.setup.container import Container
from app.config.setup.bot_registrar import BotRegistrar
# ✅ (ЗМІНЕНО) Імпортуємо функцію налаштування
from app.shared.utils.logger import setup_logging

# ================================
# 🚀 ОСНОВНА АСИНХРОННА ФУНКЦІЯ
# ================================
async def main():
    """
    Ініціалізує, запускає та коректно зупиняє всі компоненти бота.
    """
    # 1. Завантажуємо конфігурацію
    config = ConfigService()
    
    # 2. ✅ (ЗМІНЕНО) Налаштовуємо логер на основі конфігурації
    # Отримуємо секцію 'logging' з файлу config.yaml
    log_config = config.get("logging", {"level": "INFO", "console": True})
    # Налаштовуємо і отримуємо екземпляр логера
    logger = setup_logging(config=log_config)
    
    # 3. Створення DI-контейнера
    container = Container(config)


    # 5. Створення та налаштування програми бота
    application = (
        Application.builder()
        .token(config.get("telegram.bot_token"))
        .build()
    )

    # 6. Реєстрація всіх обробників
    registrar = BotRegistrar(application, container)
    registrar.register_handlers()

    # ================================
    # ▶️ ЗАПУСК ТА КОРЕКТНЕ ЗАВЕРШЕННЯ
    # ================================
    # ✅ (ЗМІНЕНО) Використовуємо наш налаштований логер замість глобального
    logger.info("🚀 Запускаю Telegram-бота...")
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        while True:
            await asyncio.sleep(3600)

    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Отримано сигнал зупинки. Завершую роботу...")
    finally:
        logger.info("🧹 Очищення ресурсів...")
        
        if application.updater and application.updater.is_running():
            await application.updater.stop()
        if application.running:
            await application.stop()
        
        logger.info("✅ Бот успішно зупинено.")

# ==========================
# 🏁 ТОЧКА ВХОДУ
# ==========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        # На випадок, якщо помилка сталася до ініціалізації нашого логера,
        # використовуємо базовий logging, щоб гарантовано записати критичну помилку.
        logging.basicConfig()
        logging.critical(f"💥 Критична помилка на верхньому рівні, що призвела до зупинки: {e}", exc_info=True)
