# 🧰 app/shared/utils/__init__.py
"""
🧰 Пакет узгоджених утиліт: логування, парсинг URL, промпти та колекції.

🔹 Агрегує ключові сервіси й допоміжні функції спільного використання.
🔹 Експортує готові обгортки для конфігурації логів та роботи з шаблонами.
🔹 Надає шляхи до стратегій парсингу, нормалізації розмірів, чисел і локалей.
🔹 Підтримує зворотну сумісність зі старими функціями `prompt_loader` та `prompts`.
"""

from __future__ import annotations

# 🔠 Логування
from .logger import (
    LOG_NAME,
    get_logger,
    init_logging,
    init_logging_from_config,
)

# 🌐 Парсинг URL
from .interfaces import IUrlParsingStrategy
from .url_parser_service import UrlParserService

# 🧾 Промпти
from .prompt_loader import load_ocr_asset, load_prompt
from .prompt_service import ChartType, PromptService, PromptType
from .prompts import (
    ChartType as LegacyChartType,
    PromptType as LegacyPromptType,
    get_prompt as _legacy_get_prompt,
    get_size_chart_prompt as _legacy_get_size_chart_prompt,
)

# 🔁 Колекції
from .collections import uniq_keep_order

# 🧊 Незмінні структури
from .immutables import FrozenMapping, freeze, is_frozen_mapping

# 🌍 Локалі
from .locale import lang_from_telegram_code, normalize_locale

# 💰 Числові утиліти
from .number import decimal_from_price_str, sanitize_price_text

# 📏 Нормалізація розмірів
from .size_norm import normalize_size_token, normalize_stock_map

# 🧾 Результати
from .result import Err, Ok, Result, is_err, is_ok, map_ok

# ================================
# 🔁 ALIASES ДЛЯ ЗВОРОТНОЇ СУМІСНОСТІ
# ================================
get_prompt = _legacy_get_prompt
get_size_chart_prompt = _legacy_get_size_chart_prompt

# ================================
# 📦 ЕКСПОРТ ПАКЕТУ
# ================================
__all__ = [
    # logging
    "LOG_NAME",
    "get_logger", 
    "init_logging",
    "init_logging_from_config",
    # url parsing
    "IUrlParsingStrategy",
    "UrlParserService",
    # prompts
    "PromptService",
    "PromptType",
    "ChartType",
    "load_prompt",
    "load_ocr_asset",
    "get_prompt",
    "get_size_chart_prompt",
    "LegacyPromptType",
    "LegacyChartType",
    # collections
    "uniq_keep_order",
    # immutables
    "FrozenMapping",
    "freeze",
    "is_frozen_mapping",
    # locales
    "normalize_locale",
    "lang_from_telegram_code",
    # number utils
    "sanitize_price_text",
    "decimal_from_price_str",
    # size normalization
    "normalize_size_token",
    "normalize_stock_map",
    # result
    "Ok",
    "Err",
    "Result",
    "is_ok",
    "is_err",
    "map_ok",
]
