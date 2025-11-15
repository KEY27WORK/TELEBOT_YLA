# 📜 app/shared/utils/logger.py
"""
📜 Єдина схема логування для всього застосунку (IMP-007).

🔹 Ініціалізує кореневий логер із консоллю та файловим виводом.
🔹 Підтримує JSON-формат, обмеження за рівнями та suppress сторонніх бібліотек.
🔹 Надає хелпера для отримання дочірніх логерів через загальний префікс.
"""
from __future__ import annotations

# 🔠 Системні імпорти
import json									# 📦 Серіалізація payload логів
import logging									# 🪵 Робота з логерами Python
import sys									# 🧵 Потоки stdout/stderr
import threading								# 🧵 Захист ініціалізації
from dataclasses import dataclass, field					# 🧱 DTO-конфіг логування
from logging.handlers import TimedRotatingFileHandler			# 📁 Хендлер з ротацією файлів
from pathlib import Path								# 📂 Операції з файловими шляхами
from typing import Any, Dict, Optional, Union				# 🧰 Типи та гібриди для конфігів

# ================================
# 🧾 КОНСТАНТИ МОДУЛЯ
# ================================
LOG_NAME: str = "telebot_ukraine_v2"					# 🏷️ Базовий префікс логерів
PLAIN_FORMAT: str = "%(asctime)s [%(levelname)s] - (%(name)s).%(funcName)s(%(lineno)d) - %(message)s"	# 📄 Формат для файлів
CONSOLE_FORMAT: str = "[%(levelname).1s] %(message)s"			# 🖥️ Мінімалістичний консольний формат

_lock = threading.Lock()							# 🔒 Блокуємо одночасну ініціалізацію


# ================================
# 🧾 DTO КОНФІГУРАЦІЇ
# ================================
@dataclass
class LoggingConfig:
    """Контейнер налаштувань логування з дефолтними значеннями."""
    level: str = "INFO"							# 🎚️ Глобальний рівень логів
    console: bool = True							# 🖥️ Чи вмикати консольний вивід
    json: bool = False								# 📦 Чи вмикати JSON-формат для файлу
    file: str = "logs/bot.log"						# 📁 Шлях до лог-файлу
    when: str = "midnight"						# ⏰ Періодичність ротації
    interval: int = 1							# ⏱️ Інтервал ротації
    backup_count: int = 7							# ♻️ Скільки копій зберігати
    encoding: str = "utf-8"							# 🔤 Кодування файлу
    suppress: Dict[str, str] = field(default_factory=dict)			# 🙊 Треті сторони та їх рівні
    console_level: str = "INFO"						# 🖥️ Рівень для консолі
    file_level: str = "DEBUG"						# 📁 Рівень для файлу
    console_format: str = CONSOLE_FORMAT				# 🖥️ Шаблон для консолі
    file_format: str = PLAIN_FORMAT					# 📄 Шаблон для файлу


# ================================
# 🧰 ФОРМАТТЕРИ
# ================================
class JsonFormatter(logging.Formatter):
    """Форматує записи логів у плоский JSON-представник."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S"),	# ⏱️ Час події
            "level": record.levelname,					# 🎚️ Рівень логування
            "name": record.name,						# 🏷️ Імʼя логера
            "module": record.module,					# 🧩 Модуль джерела
            "func": record.funcName,					# 🧮 Функція джерела
            "line": record.lineno,						# 📍 Номер рядка
            "message": record.getMessage(),				# 🗒️ Повідомлення
        }
        for key, value in record.__dict__.items():			# 🔎 Додаємо custom extra-поля
            if key.startswith("_") or key in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "levelname",
                "funcName",
            ):
                continue
            if key not in payload:					# 🧩 Уникаємо перезапису базових полів
                try:
                    json.dumps(value)				# ✅ Перевіряємо серіалізованість
                    payload[key] = value				# 🗃️ Зберігаємо у payload
                except Exception:					# noqa: BLE001	# ⚠️ Нестерилізований обʼєкт
                    payload[key] = str(value)			# 🔄 Повертаємось до рядка
        if record.exc_info:						# ⚠️ Додаємо інформацію про виняток
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)		# 🌐 Зберігаємо юнікод


# ================================
# 🛠️ ДОПОМОЖНІ ФУНКЦІЇ
# ================================
def _make_console_handler(fmt: logging.Formatter) -> logging.Handler:
    """Створює консольний хендлер із заданим форматером."""
    handler = logging.StreamHandler(sys.stdout)			# 🖥️ Потік stdout
    handler.setFormatter(fmt)						# 🪄 Застосовуємо форматування
    return handler									# 📦 Повертаємо готовий хендлер


def _make_file_handler(cfg: LoggingConfig, fmt: logging.Formatter) -> logging.Handler:
    """Готує файловий хендлер із ротацією за часом."""
    log_path = Path(cfg.file)						# 📂 Конвертуємо шлях
    log_path.parent.mkdir(parents=True, exist_ok=True)		# 🧱 Гарантуємо існування директорії
    handler = TimedRotatingFileHandler(
        filename=cfg.file,
        when=cfg.when,
        interval=cfg.interval,
        backupCount=cfg.backup_count,
        encoding=cfg.encoding,
    )									# ⏰ Налаштовуємо ротацію
    handler.setFormatter(fmt)						# 🪄 Задаємо формат для файлу
    return handler								# 📦 Повертаємо хендлер


def _suppress_third_party(suppress: Dict[str, str]) -> None:
    """Знижує рівні логування для сторонніх бібліотек."""
    for name, level in (suppress or {}).items():			# 🔁 Перебираємо записані винятки
        target_level = getattr(logging, str(level).upper(), logging.WARNING)	# 🎚️ Конвертуємо у рівень
        logging.getLogger(name).setLevel(target_level)		# 🙊 Встановлюємо рівень на логері


# ================================
# 🚀 ПУБЛІЧНИЙ API
# ================================
def init_logging(
    *,
    level: Optional[str] = None,
    console: Optional[bool] = None,
    json_mode: Optional[bool] = None,
    file: Optional[str] = None,
    suppress: Optional[Dict[str, str]] = None,
    console_level: Optional[Union[str, int]] = None,
    file_level: Optional[Union[str, int]] = None,
    console_format: Optional[str] = None,
    file_format: Optional[str] = None,
) -> logging.Logger:
    """Ініціалізує кореневий логер застосунку за єдиною схемою."""
    with _lock:									# 🔒 Блокуємо повторну конфігурацію
        cfg = LoggingConfig(
            level=level or "INFO",						# 🎚️ Загальний рівень
            console=True if console is None else bool(console),			# 🖥️ Вмикаємо консоль за замовчуванням
            json=False if json_mode is None else bool(json_mode),		# 📦 JSON-формат для файлу
            file=file or "logs/bot.log",					# 📁 Шлях до файлу
            suppress=suppress or {},					# 🙊 Конфіг подавлення сторонніх бібліотек
            console_level=str(console_level or level or "INFO"),		# 🖥️ Рівень консолі
            file_level=str(file_level or level or "INFO"),			# 📁 Рівень файлу
            console_format=console_format or CONSOLE_FORMAT,		# 🖥️ Шаблон консольного виводу
            file_format=file_format or PLAIN_FORMAT,			# 📄 Шаблон файлового виводу
        )								# 📦 Упаковуємо конфіг

        root_logger = logging.getLogger(LOG_NAME)			# 🏷️ Кореневий логер застосунку

        def _to_level(value: Union[str, int], default: int) -> int:
            """Перетворює рядок/інт у числовий рівень логування."""
            if isinstance(value, int):					# 🔢 Вже числовий рівень
                return value						# 🔙 Повертаємо як є
            return getattr(logging, str(value).upper(), default)	# 🎚️ Конвертуємо рядок у рівень

        root_level = min(
            _to_level(cfg.level, logging.INFO),				# 🎚️ Глобальний рівень
            _to_level(cfg.console_level, logging.INFO),		# 🖥️ Рівень консолі
            _to_level(cfg.file_level, logging.INFO),			# 📁 Рівень файлу
        )								# 🧮 Визначаємо нижню межу
        root_logger.setLevel(root_level)				# 🔧 Встановлюємо кореневий рівень

        for handler in list(root_logger.handlers):			# 🧹 Очищаємо попередні хендлери
            if isinstance(handler, (logging.StreamHandler, TimedRotatingFileHandler)):
                root_logger.removeHandler(handler)			# 🗑️ Прибираємо наші

        fmt_console = logging.Formatter(cfg.console_format)		# 🖥️ Форматер консолі
        fmt_file = JsonFormatter() if cfg.json else logging.Formatter(cfg.file_format)	# 📄 Обираємо формат для файлу

        if cfg.console:							# ✅ Консоль увімкнено
            console_handler = _make_console_handler(fmt_console)	# 🛠️ Створюємо консольний хендлер
            console_handler.setLevel(_to_level(cfg.console_level, logging.INFO))	# 🎚️ Рівень консолі
            root_logger.addHandler(console_handler)			# ➕ Додаємо до кореня

        file_handler = _make_file_handler(cfg, fmt_file)		# 📁 Створюємо файловий хендлер
        file_handler.setLevel(_to_level(cfg.file_level, logging.DEBUG))	# 🎚️ Рівень файлу
        root_logger.addHandler(file_handler)				# ➕ Додаємо до кореня

        _suppress_third_party(cfg.suppress)				# 🙊 Налаштовуємо сторонні логери

        root_logger.info(
            "✅ Logging initialized | level=%s console=%s/%s json=%s file=%s/%s",
            cfg.level.upper(),
            "ON" if cfg.console else "OFF",
            cfg.console_level.upper(),
            "ON" if cfg.json else "OFF",
            cfg.file,
            cfg.file_level.upper(),
        )								# 🧾 Фіксуємо результат ініціалізації
        return root_logger						# 📬 Повертаємо готовий логер


def init_logging_from_config(config: Dict[str, Any]) -> logging.Logger:
    """
    Ініціалізує логування на базі словника з конфігураційного сервісу.

    Args:
        config: Налаштування розділу `logging` із ConfigService.

    Returns:
        logging.Logger: Кореневий логер, проініціалізований за наданими параметрами.
    """
    node = config or {}							# 🧾 Гарантуємо словник
    return init_logging(
        level=node.get("level"),
        console=node.get("console"),
        json_mode=node.get("json"),
        file=node.get("file"),
        suppress=node.get("suppress"),
        console_level=node.get("console_level"),
        file_level=node.get("file_level"),
        console_format=node.get("console_format"),
        file_format=node.get("file_format"),
    )									# 🔁 Делегуємо у базову функцію


def get_logger(suffix: Optional[str] = None) -> logging.Logger:
    """
    Повертає дочірній логер із префіксом `LOG_NAME`.

    Args:
        suffix: Опційний суфікс, що додається через крапку.

    Returns:
        logging.Logger: Обмежений або кореневий логер із узгодженою назвою.
    """
    logger_name = LOG_NAME if not suffix else f"{LOG_NAME}.{suffix}"	# 🏷️ Формуємо імʼя логера
    return logging.getLogger(logger_name)				# 📬 Повертаємо дочірній логер
