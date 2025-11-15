# ♻️ app/shared/cache/html_lru_cache.py
"""
♻️ Асинхронний LRU+TTL кеш для HTML-документів.

🔹 Підтримує обмеження за кількістю елементів (LRU) та часом життя (TTL).
🔹 Гарантує, що паралельні запити до одного ключа синхронізуються через locks.
🔹 Використовується для кешування HTML, отриманих від веб-драйвера/HTTP-клієнтів.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio                                         # 🧵 Асинхронні locks
import time                                            # ⏱️ Вимірювання TTL
from collections import OrderedDict                   # 🔁 Реалізація LRU
from typing import Dict, Optional, Tuple              # 🧰 Типи допоміжних структур

# ================================
# 🔒 ВНУТРІШНІЙ LRU-КОНТЕЙНЕР
# ================================
class _LRU:
    """Внутрішня реалізація LRU з підтримкою TTL."""

    def __init__(self, max_entries: int, ttl_sec: int) -> None:
        self.max = int(max_entries)                    # 🔢 Максимальна кількість записів
        self.ttl = int(ttl_sec)                        # ⏳ Час життя запису
        self._data: "OrderedDict[str, Tuple[float, str]]" = OrderedDict()  # 🗂️ Сховище (timestamp, html)

    def get(self, key: str) -> Optional[str]:
        """Повертає HTML, якщо запис ще валідний, інакше очищає кеш."""
        now = time.time()                              # ⏱️ Поточний час
        item = self._data.get(key)                     # 🔎 Пошук у кеші
        if not item:                                   # 🚫 Немає запису
            return None
        timestamp, html = item                         # 📦 Розпаковуємо кешований запис
        if self.ttl > 0 and (now - timestamp) > self.ttl:  # ⏰ TTL вичерпано
            self._data.pop(key, None)                  # 🧹 Видаляємо застарілий запис
            return None
        self._data.move_to_end(key, last=True)         # 🔁 Переносимо в кінець (найсвіжіше використання)
        return html                                    # 📬 Повертаємо HTML

    def set(self, key: str, html: str) -> None:
        """Оновлює HTML у кеші з міткою часу."""
        self._data[key] = (time.time(), html)          # 📝 Зберігаємо поточний час та HTML
        self._data.move_to_end(key, last=True)         # 🔁 Позначаємо як найсвіжіший
        while len(self._data) > self.max:              # 🔄 Прибираємо найстаріші записи
            self._data.popitem(last=False)             # 🚮 Виселяємо елемент з голови OrderedDict


# ================================
# ♻️ СИНГЛТОН HTML-КЕШУ
# ================================
class HtmlLruCache:
    """Процесний async-safe кеш HTML з LRU та TTL."""

    _instance: Optional["HtmlLruCache"] = None         # 🧠 Синглтон кешу
    _lru: Optional[_LRU] = None                        # ♻️ Внутрішній LRU-контейнер
    _locks: Dict[str, asyncio.Lock] = {}               # 🔐 Блокування на ключ
    _global_lock: Optional[asyncio.Lock] = None        # 🔐 Глобальний lock для створення key-locks

    def __new__(cls, max_entries: int = 256, ttl_sec: int = 300) -> "HtmlLruCache":
        """Забезпечує єдиний екземпляр кешу з заданими параметрами."""
        if cls._instance is None:                      # 🧠 Створюємо синглтон
            cls._instance = super().__new__(cls)
            cls._instance._lru = _LRU(max_entries, ttl_sec)  # ♻️ Ініціалізуємо LRU
            cls._instance._locks = {}
            cls._instance._global_lock = asyncio.Lock()
        return cls._instance

    async def get(self, key: str) -> Optional[str]:
        """Повертає HTML з кешу або None, якщо запис відсутній."""
        assert self._lru is not None                   # 🛡️ Захисна перевірка
        return self._lru.get(key)                      # ♻️ Дістаємо з LRU

    async def set(self, key: str, html: str) -> None:
        """Зберігає HTML у кеші, якщо він непорожній."""
        if html:                                       # ✅ Ігноруємо порожні значення
            assert self._lru is not None
            self._lru.set(key, html)                   # 📝 Оновлюємо кеш

    async def key_lock(self, key: str) -> asyncio.Lock:
        """Повертає асинхронний lock для конкретного ключа."""
        assert self._global_lock is not None           # 🛡️ Маємо глобальний lock
        async with self._global_lock:                  # 🔒 Створюємо/шукаємо локальний lock під захистом
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()      # 🆕 Створюємо lock для ключа
            return self._locks[key]                    # 🔁 Повертаємо існуючий lock
