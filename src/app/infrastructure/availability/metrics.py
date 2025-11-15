# 📈 app/infrastructure/availability/metrics.py
"""
📈 Prometheus-метрики для підсистеми наявності (`Availability`).

🔹 `AV_CACHE_HITS` / `AV_CACHE_MISSES` — лічильники кеш-хітів/промахів.  
🔹 `AV_REPORT_LATENCY` — гістограма часу побудови звіту про наявність.  
🔹 Метрики експортуються як константи й можуть використовуватися в будь-якому сервісі.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from prometheus_client import Counter, Histogram                      # 📊 Prometheus-метрики

# ================================
# 📊 ЛІЧИЛЬНИКИ КЕША
# ================================
AV_CACHE_HITS = Counter(
    "availability_cache_hits_total",                                 # 🏷️ Імʼя метрики
    "Cache hits for availability reports",                           # 📝 Опис у Prometheus
)

AV_CACHE_MISSES = Counter(
    "availability_cache_misses_total",                               # 🏷️ Імʼя метрики
    "Cache misses for availability reports",                         # 📝 Опис
)

# ================================
# ⏱️ ГІСТОГРАМА ЛАТЕНТНОСТІ
# ================================
AV_REPORT_LATENCY = Histogram(
    "availability_report_seconds",                                   # 🏷️ Базова назва гістограми
    "Time to build availability report",                             # 📝 Опис
)


__all__ = [
    "AV_CACHE_HITS",
    "AV_CACHE_MISSES",
    "AV_REPORT_LATENCY",
]
