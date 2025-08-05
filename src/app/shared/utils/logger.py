# 🧰 app/shared/utils/logger.py
"""
🧰 logger.py — Централізований модуль для налаштування логування.

🔹 Налаштовує єдиний логер для проєкту.
🔹 Дозволяє керувати рівнем логування, виводом у консоль та фільтрацією
   через конфігураційний файл.
🔹 Використовує ротацію лог-файлів.
"""

# 🔠 Системні імпорти
import logging										                                                                    # 🧾 Базовий модуль для логування
import sys												                                                                # 🖥️ Для виводу в консоль (stdout)
from logging.handlers import TimedRotatingFileHandler	                                                                # 📁 Обробник з ротацією логів по часу
from pathlib import Path								                                                                # 📂 Робота з файловою системою (директорія logs)
from typing import Dict, Any							                                                                # 🧰 Типи для конфігурацій


# ==========================
# ⚙️ КОНСТАНТИ
# ==========================
LOG_NAME = "telebot_ukraine_v2"						                                                                    # 🏷️ Імʼя логера
LOG_FORMAT = "%(asctime)s [%(levelname)s] - (%(name)s).%(funcName)s(%(lineno)d) - %(message)s"	                        # 🧾 Формат логів


# ==========================
# 🕵️‍♂️ ПРИВАТНІ ДОПОМІЖНІ ФУНКЦІЇ
# ==========================

def _create_console_handler() -> logging.StreamHandler:
	"""
	🖥️ Створює обробник для виводу логів у консоль.
	"""
	console_handler = logging.StreamHandler(sys.stdout)				                                                    # 📤 Вивід у stdout
	console_handler.setFormatter(logging.Formatter(LOG_FORMAT))	                                                        # 🧾 Форматування
	return console_handler

def _create_file_handler() -> TimedRotatingFileHandler:
	"""
	📄 Створює обробник для запису логів у файл з щоденною ротацією.
	"""
	log_dir = Path("logs")									                                                            # 📂 Каталог для логів
	log_dir.mkdir(exist_ok=True)								                                                        # ✅ Створити, якщо не існує
	log_file = log_dir / "bot.log"							                                                            # 📄 Повний шлях до файлу логів

	file_handler = TimedRotatingFileHandler(
		log_file,
		when="midnight",
		interval=1,
		backupCount=7,
		encoding="utf-8"
	)
	file_handler.setFormatter(logging.Formatter(LOG_FORMAT))		                                                    # 🧾 Форматування
	return file_handler

def _suppress_third_party_loggers(suppress_config: Dict[str, str]):
	"""
	🔇 Встановлює вищий рівень логування для "галасливих" бібліотек.
	"""
	for name, level in suppress_config.items():						                                                    # 🔁 Ітеруємо всі імена логерів
		logging.getLogger(name).setLevel(level.upper())				                                                    # 🚫 Підвищуємо рівень (наприклад WARNING)


# ==========================
# 🏛️ ГОЛОВНА ФУНКЦІЯ НАЛАШТУВАННЯ
# ==========================

def setup_logging(config: Dict[str, Any]) -> logging.Logger:
	"""
	Налаштовує єдиний логер для всього проєкту на основі конфігурації.

	Args:
		config (Dict[str, Any]): Словник з налаштуваннями логування.

	Returns:
		logging.Logger: Сконфігурований екземпляр логера.
	"""
	level = config.get("level", "INFO")							                                                        # 🧾 Рівень логування (default: INFO)
	enable_console = config.get("console", True)					                                                    # 🖥️ Виводити в консоль чи ні
	suppress_list = config.get("suppress", {})					                                                        # 🔕 Тихі логери

	logger = logging.getLogger(LOG_NAME)							                                                    # 🏷️ Отримуємо головний логер
	log_level = logging.getLevelName(level.upper())				                                                        # 🔠 Рівень (INFO, DEBUG, тощо)
	logger.setLevel(log_level)

	if logger.hasHandlers():										                                                    # 🔁 Якщо вже налаштовано
		logger.handlers.clear()									                                                        # ❌ Очистити старі обробники

	if enable_console:
		logger.addHandler(_create_console_handler())				                                                    # 🖥️ Додаємо консольний обробник

	logger.addHandler(_create_file_handler())						                                                    # 📄 Додаємо файловий обробник

	_suppress_third_party_loggers(suppress_list)					                                                    # 🔇 Фільтруємо галасливі логери

	logger.info(                                                                                                        # ✅ Успішна ініціалізація
		f"✅ Логування налаштовано. Рівень: {level.upper()}. Консоль: {'ON' if enable_console else 'OFF'}."
		)	
	return logger												                                                        # 🔁 Повертаємо логер
