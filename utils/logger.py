""" 🧾 logger.py — конфігурація логування з підтримкою ротації лог-файлів.

🔹 Клас `Logger`:
- Створює та конфігурує логгер з ім'ям "BotLogger"
- Пише логи у файл `bot.log`
- Пише логи також у консоль (термінал)
- Автоматично створює новий лог-файл, коли розмір перевищує 5 MB
- Зберігає до 3 резервних лог-файлів

Використовує:
- logging (вбудований модуль Python)
- RotatingFileHandler для обмеження розміру логів
"""

# 🧱 Системні імпорти
import os
import logging
from logging.handlers import RotatingFileHandler


class Logger:
    """📋 Клас для налаштування глобального логгера бота."""

    @staticmethod
    def setup_logger():
        """ 🛠️ Налаштовує логгер:
        - Ім'я: "BotLogger"
        - Рівень: DEBUG
        - Файл: bot.log
        - Ротація: 5MB, 3 файли
        - Консоль: виводить логи також у термінал

        :return: Конфігурований логгер
        """
        logger = logging.getLogger("BotLogger")
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # 📁 Шлях до папки логів
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "bot.log")

        # 📁 Файл логів з ротацією
        file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
        file_handler.setFormatter(formatter)

        # 📺 Логи в консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # 🔁 Уникаємо дублювання, якщо вже є хендлери
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        return logger
