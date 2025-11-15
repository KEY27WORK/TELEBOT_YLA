# 💾 app/infrastructure/availability/cache_service.py
"""
💾 Thread-safe in-memory кеш з TTL для Availability Reports.

🔹 Backward-compatible API: `get(key, ttl)` / `set(key, data)` з TTL «на читанні».  
🔹 Підтримка `set_with_ttl`, `get_or_set`, `prune_expired`, `stats`, `invalidate`, `clear`.  
🔹 Монотонний годинник і RLock → безпечний у багатопоточному середовищі.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логи роботи кешу
import time                                                         # ⏱️ Монотонний годинник
from dataclasses import dataclass                                   # 📦 Внутрішні структури
from datetime import timedelta                                     # 🕒 TTL у timedelta
from threading import RLock                                         # 🔒 Потокобезопасний доступ
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union  # 📐 Типи API

logger = logging.getLogger(__name__)                                # 🧾 Локальний логер кешу

T = TypeVar("T")


# ================================
# ⏱️ ДОПОМІЖНІ УТИЛІТИ
# ================================
def _now() -> float:
    """Поточний монотонний час (секунди)."""
    now = time.monotonic()                                          # ⏱️ Переконуємось, що час монотонний
    logger.debug("⏱️ _now=%s", now)
    return now


def _normalize_ttl(ttl: Optional[Union[int, float, timedelta]]) -> float:
    """Приводить TTL до секундів (float ≥ 0)."""
    if ttl is None:
        return 0.0                                                   # 🔁 TTL не задано → 0
    if isinstance(ttl, timedelta):
        return max(0.0, ttl.total_seconds())                         # 🕒 Беремо секундний еквівалент
    try:
        return max(0.0, float(ttl))                                  # 🔢 Пробуємо привести до float
    except (TypeError, ValueError):
        logger.warning("⚠️ Некоректний TTL: %r", ttl)
        return 0.0


# ================================
# 📦 ВНУТРІШНІ ЕЛЕМЕНТИ КЕШУ
# ================================
@dataclass(slots=True)
class _CacheItem:
    data: Any                                                        # 📄 Збережені дані
    expires_at: float                                                # ⏳ 0.0 → TTL на читанні


# ================================
# 💾 ОСНОВНИЙ КЕШ
# ================================
class AvailabilityCacheService(Generic[T]):
    """💾 Thread-safe кеш з TTL (сумісний зі старим API)."""

    def __init__(self, *, max_items: Optional[int] = None) -> None:
        self._cache: Dict[str, _CacheItem] = {}                       # 📦 Основне сховище
        self._lock = RLock()                                          # 🔒 Потокобезпечність
        self._last_prune_at: float = 0.0                              # 🕒 Час останнього prune
        self._evictions: int = 0                                      # 🚪 Виселення через перевищення ліміту
        self._max_items = max(1, int(max_items)) if max_items else None  # 📏 Опціональний ліміт
        logger.debug("⚙️ Cache init (max_items=%s)", self._max_items)

    def get(self, key: str, ttl: Union[int, float, timedelta]) -> Optional[T]:
        """Читає дані, враховуючи TTL (на читанні або `expires_at`)."""
        ttl_sec = _normalize_ttl(ttl)
        with self._lock:
            item = self._cache.get(key)                               # 🔍 Пробуємо отримати елемент
            if item is None:
                logger.debug("🔍 cache miss: %s", key)
                return None

            now = _now()                                              # ⏱️ Поточний час
            effective_expires_at = item.expires_at or (now + ttl_sec)
            if now < effective_expires_at:
                logger.debug("✅ cache hit: %s", key)
                return item.data  # type: ignore[return-value]

            logger.debug("⌛ cache expired: %s", key)
            self._cache.pop(key, None)
            return None

    def set(self, key: str, data: T) -> None:
        """Зберігає без фіксованого TTL (expires_at=0)."""
        with self._lock:                                              # 🔐 Гарантуємо атомарність операції
            self._maybe_compact_locked()                             # 🧯 Перевіряємо ліміт перед записом
            self._cache[key] = _CacheItem(data=data, expires_at=0.0) # 💾 TTL застосовується «на читанні»
            logger.debug("💾 set: %s", key)                          # 🪵 Логуємо збереження ключа

    def set_with_ttl(self, key: str, data: T, ttl: Union[int, float, timedelta]) -> None:
        """Запис із заздалегідь зафіксованим TTL."""
        ttl_sec = _normalize_ttl(ttl)                                # ⏱️ Нормалізуємо TTL у секундах
        with self._lock:                                             # 🔐 Секція під блокуванням
            self._maybe_compact_locked()                             # 🧯 Можливе pruning перед записом
            expires = (_now() + ttl_sec) if ttl_sec > 0 else 0.0     # ⏳ Фіксуємо момент закінчення
            self._cache[key] = _CacheItem(data=data, expires_at=expires)
            logger.debug("💾 set_with_ttl: %s ttl=%s", key, ttl_sec) # 🪵 Фіксуємо TTL-оновлення

    def get_or_set(self, key: str, ttl: Union[int, float, timedelta], supplier: Callable[[], T]) -> T:
        """🦥 Повертає значення або створює через supplier()."""
        existing = self.get(key, ttl)                                # 🔄 Прагнемо повторно використати кеш
        if existing is not None:                                     # ✅ Знаходимо готовий результат
            return existing                                          # ↩️ Повертаємо кешовані дані
        fresh = supplier()                                            # 🆕 Генеруємо нове значення
        self.set(key, fresh)                                         # 💾 Записуємо в кеш для наступних викликів
        logger.debug("🆕 get_or_set stored: %s", key)                # 🪵 Логуємо новий запис
        return fresh                                                 # 📦 Віддаємо щойно отримані дані

    def invalidate(self, key: str) -> None:
        """🧹 Видаляє окремий ключ із кешу."""
        with self._lock:                                             # 🔐 Синхронізуємо доступ
            removed = self._cache.pop(key, None)                     # 🧹 Якщо ключа немає — нічого не станеться
            logger.debug("🧹 invalidate %s removed=%s", key, removed is not None)  # 🪵 Логуємо факт видалення

    def clear(self) -> None:
        """🧼 Повністю очищає кеш."""
        with self._lock:                                             # 🔐 Уникаємо гонок під час очищення
            self._cache.clear()                                      # 🧼 Скидаємо всі записи та статистику
            logger.info("🧼 Cache cleared")                          # 🪵 Повідомляємо про повне очищення

    def prune_expired(self) -> int:
        """🔪 Видаляє прострочені елементи, повертає кількість."""
        now = _now()                                                  # ⏱️ Фіксуємо момент перевірки
        removed = 0                                                  # 🔢 Лічильник видалених елементів
        with self._lock:                                             # 🔐 Працюємо під блокуванням
            to_delete = [
                k
                for k, item in self._cache.items()
                if item.expires_at and now >= item.expires_at
            ]  # 🗑️ Перелік прострочених ключів
            for key in to_delete:                                    # 🔁 Проходимо всі прострочені
                self._cache.pop(key, None)                           # 🔪 Видаляємо прострочений ключ
                removed += 1                                         # 🔢 Лічильник видалених значень
            self._last_prune_at = now                               # 🕒 Фіксуємо час чистки
        logger.info("✂️ prune_expired removed=%d", removed)          # 🪵 Репортуємо статистику чистки
        return removed                                               # 🔢 Повертаємо кількість видалених

    def stats(self) -> Dict[str, int | float]:
        """📈 Повертає прості метрики кешу."""
        now = _now()                                                  # ⏱️ Обчислюємо live-значення на момент виклику
        with self._lock:
            total = len(self._cache)
            live = sum(1 for item in self._cache.values() if item.expires_at == 0.0 or now < item.expires_at)
            stats = {
                "items_total": total,                                 # 📦 Усього записів
                "items_live": live,                                   # 🌱 Живі (не прострочені)
                "last_prune_at": self._last_prune_at,                 # ⏱️ Останній prune
                "evictions": self._evictions,                         # 🚪 Виселення через ліміт
            }
            logger.debug("📊 stats=%s", stats)
            return stats

    def _maybe_compact_locked(self) -> None:
        """🧯 Контролює ліміт max_items (prune → eviction)."""
        if self._max_items is None or len(self._cache) < self._max_items:
            return

        self.prune_expired()                                          # 🧹 Спочатку прибираємо прострочене
        if len(self._cache) < self._max_items:
            return

        try:
            victim_key = next(iter(self._cache.keys()))               # 🎯 Беремо довільний ключ
        except StopIteration:
            return
        self._cache.pop(victim_key, None)
        self._evictions += 1
        logger.warning("⚠️ Evicted %s (max_items=%s)", victim_key, self._max_items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._cache


__all__ = ["AvailabilityCacheService"]
