# 📊 app/shared/metrics/__init__.py
"""
📊 Пакет агрегованих метрик Prometheus для застосунку.

🔹 Охоплює контентні, OCR- та парсингові лічильники.
🔹 Містить легкий bootstrap експортер `/metrics`.
🔹 Сприяє централізованому моніторингу сервісів.
"""

from __future__ import annotations

# 🔢 Контентні метрики
from .content import ALT_CACHE_HIT, ALT_FAILURE, ALT_SUCCESS

# 🔁 Parsers & OCR
from .ocr import OCR_CACHE_HIT, OCR_CACHE_MISS, OCR_FAILURE, OCR_SUCCESS
from .parsing import PARSING_FAILURE, PARSING_SUCCESS

# 🚀 Експортер Prometheus
from .exporters import maybe_start_prometheus

# ================================
# 📦 ЕКСПОРТ ПАКЕТУ
# ================================
__all__ = [
    "ALT_SUCCESS",
    "ALT_FAILURE",
    "ALT_CACHE_HIT",
    "OCR_SUCCESS",
    "OCR_FAILURE",
    "OCR_CACHE_HIT",
    "OCR_CACHE_MISS",
    "PARSING_SUCCESS",
    "PARSING_FAILURE",
    "maybe_start_prometheus",
]
