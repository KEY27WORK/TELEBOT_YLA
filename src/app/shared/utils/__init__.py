# 🧰 app/shared/utils/__init__.py
"""
🧰 Пакет `utils`

Містить утиліти та сервісні класи, що використовуються в різних шарах архітектури.

📦 Основні компоненти:
- Логер (`logger.py`)
- Парсер URL-адрес (`url_parser_service.py`)
- Низькорівневі компоненти для генерації промтів (`prompts.py`, `prompt_loader.py`)
"""

# 🧾 Логування
from .logger import setup_logging, LOG_NAME

# 🌐 Парсинг URL
from .url_parser_service import UrlParserService

# 🧠 Генерація промтів (низькорівневі компоненти)
from .prompts import PromptType, ChartType, get_prompt, get_size_chart_prompt
from .prompt_loader import load_prompt, load_ocr_asset

__all__ = [
    # 🧾 Логування
    "setup_logging",
    "LOG_NAME",

    # 🌐 Парсинг URL
    "UrlParserService",

    # 🧠 Генерація промтів
    "PromptType",
    "ChartType",
    "get_prompt",
    "get_size_chart_prompt",
    "load_prompt",
    "load_ocr_asset",
]
