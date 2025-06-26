""" 🧾 logger.py — конфігурація логування з підтримкою ротації лог-файлів.

🔹 Клас `Logger`:
- Налаштовує глобальний логгер (root logger), який працює для всіх модулів
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
        """
        🛠️ Налаштовує root logger (глобальний логгер для всієї програми):
        - Рівень: DEBUG
        - Формат: [час] [рівень] [модуль] повідомлення
        - Файл логів: logs/bot.log (з ротацією)
        - Консоль: виводить у stdout
        """
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

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

        # 📌 Налаштовуємо root logger
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[file_handler, console_handler],
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
