# ⚖️ app/infrastructure/data_storage/weight_data_service.py
"""
⚖️ WeightDataService — асинхронне сховище ваг (грами) з кешем і debounced-флашем.

🔹 Реалізує доменний контракт `IWeightDataProvider` — працює лише з int (грами).
🔹 Ліниво завантажує JSON у памʼять, конвертує старі формати (кг/float/str) у грами.
🔹 Debounce-запис: зміни накопичуються та зберігаються в файл з невеликою затримкою.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import aiofiles	# 📄 Асинхронне читання/запис JSON-файлу

# 🔠 Системні імпорти
import asyncio	# 🔁 Lock, debounce, фонова задача
import json	# 📄 Робота з JSON-файлом
import logging	# 🧾 Логування операцій
import os	# 🗂️ Атомарний rename/перевірка файлів
from pathlib import Path	# 📁 Створення директорії
from typing import Dict, Optional	# 🧰 Типи для кешу

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService	# ⚙️ Конфіг
from app.domain.products.interfaces import IWeightDataProvider	# 📦 Доменний контракт
from app.shared.utils.logger import LOG_NAME	# 🏷️ Імʼя базового логера

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)	# 🧾 Використовуємо загальний логер


def _to_int_grams(value: object) -> Optional[int]:
    """🧮 Конвертує довільне значення у грами, повертає None, якщо привести неможливо."""
    if isinstance(value, int):  # ✅ Уже int → припускаємо грами
        return value if value >= 0 else None
    if isinstance(value, float):  # ✅ float → якщо < 50, трактуємо як кг
        if value < 0:
            return None
        grams = int(round(value * 1000)) if value < 50.0 else int(round(value))
        return grams
    if isinstance(value, str):  # 🧵 Рядок → пробуємо int, потім float
        sanitized = value.strip().replace(",", ".")
        try:
            parsed_int = int(sanitized)
            return parsed_int if parsed_int >= 0 else None
        except Exception:
            pass
        try:
            parsed_float = float(sanitized)
            if parsed_float < 0:
                return None
            grams = int(round(parsed_float * 1000)) if parsed_float < 50.0 else int(round(parsed_float))
            return grams
        except Exception:
            return None
    return None  # 🪣 Невідомий тип → відкидаємо


# ================================
# 🏛️ СЕРВІС
# ================================
class WeightDataService(IWeightDataProvider):
    """⚖️ Локальне сховище ваг із асинхронним кешем та відкладеним записом."""

    def __init__(self, config: ConfigService) -> None:
        self._file_path = str(config.get("files.weights", "weights.json"))	# 🗂️ Шлях до файлу ваг
        self._flush_sec = float(config.get("weights.flush_sec", 1.5) or 1.5)	# ⏱️ Debounce затримка
        self._ensure_dir = bool(config.get("weights.ensure_dir", True))	# 🏗️ Створювати директорію

        self._lock = asyncio.Lock()	# 🔐 Захист доступу до кешу/запису
        self._cache: Optional[Dict[str, int]] = None	# 🧠 Лінивий кеш
        self._flush_task: Optional[asyncio.Task] = None	# ⏳ Поточна debounce-задача

        if self._ensure_dir:
            try:
                Path(self._file_path).parent.mkdir(parents=True, exist_ok=True)	# 🏗️ Створюємо директорію
            except Exception as exc:
                logger.warning("⚠️ Не вдалося створити директорію для %s: %s", self._file_path, exc)

        logger.info("⚖️ WeightDataService init (file=%s, flush=%.2fs)", self._file_path, self._flush_sec)

    # ================================
    # 📣 ПУБЛІЧНИЙ КОНТРАКТ
    # ================================
    async def get_all_weights(self) -> Dict[str, int]:
        """📖 Повертає копію актуальних ваг із кешу (авто-завантажує JSON)."""
        async with self._lock:
            await self._ensure_cache_loaded()
            return dict(self._cache or {})	# 🧾 Копія, щоб зовні не змінювали кеш

    async def update_weight(self, keyword: str, weight_g: int) -> None:
        """🔄 Оновлює вагу (грами) та планує debounced-флаш."""
        key = (keyword or "").strip().lower()	# 🏷️ Нормалізуємо ключ
        if not key:
            raise ValueError("Порожній ключ ваги (keyword).")
        if not isinstance(weight_g, int) or weight_g < 0:
            raise ValueError("weight_g має бути невідʼємним int у грамах.")

        async with self._lock:
            await self._ensure_cache_loaded()
            assert self._cache is not None
            self._cache[key] = weight_g	# ♻️ Оновлюємо кеш
            logger.info("♻️ Вага оновлена: %s = %d г", key, weight_g)
            self._schedule_flush_locked()	# 🕒 Debounce-запис

    # ================================
    # 🧠 ВНУТРІШНЯ ЛОГІКА
    # ================================
    async def _ensure_cache_loaded(self) -> None:
        """📥 Ліниво завантажує JSON у кеш, конвертуючи всі значення в грами."""
        if self._cache is not None:  # ✅ Уже завантажено
            return
        try:
            async with aiofiles.open(self._file_path, "r", encoding="utf-8") as file_handle:
                content = await file_handle.read()  # 📄 Читаємо файл
            raw = json.loads(content) if content else {}  # 🧾 Розбираємо JSON
            if not isinstance(raw, dict):  # 🛑 Очікуємо обʼєкт
                raise ValueError("Очікувався JSON-об'єкт із вагами.")
            cache: Dict[str, int] = {}
            for key, value in raw.items():  # 🔁 Конвертуємо кожен запис
                grams = _to_int_grams(value)
                if grams is not None:
                    cache[str(key).lower()] = grams  # 🧮 Зберігаємо у грамах
            self._cache = cache
            logger.info("📖 Кеш ваг завантажено: %d запис(ів).", len(self._cache))
        except FileNotFoundError:
            logger.info("📄 Файл ваг не знайдено, стартуємо з порожнього кешу.")
            self._cache = {}
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("⚠️ Некоректний формат файлу ваг (%s). Стартуємо з порожнього кешу.", exc)
            self._cache = {}

    def _schedule_flush_locked(self) -> None:
        """🕒 Плануємо відкладений запис (під lock)."""
        if self._flush_task and not self._flush_task.done():  # ♻️ Скасовуємо попередній debounce
            self._flush_task.cancel()
        self._flush_task = asyncio.create_task(self._delayed_flush())  # ⏳ Запускаємо нову задачу

    async def _delayed_flush(self) -> None:
        """⏳ Чекає дебаунс і виконує запис у файл."""
        try:
            await asyncio.sleep(max(0.0, float(self._flush_sec)))  # 😴 Чекаємо зазначену затримку
            async with self._lock:
                await self._flush_now_locked()  # 💾 Зберігаємо під lock
        except asyncio.CancelledError:
            return  # 🔁 Debounce: задача скасована іншою подією
        except Exception:
            logger.exception("❌ Помилка під час відкладеного збереження ваг.")

    async def _flush_now_locked(self) -> None:
        if self._cache is None:
            return
        payload_obj = dict(sorted(self._cache.items()))	# 📚 Стабільний порядок
        payload = json.dumps(payload_obj, indent=2, ensure_ascii=False)
        tmp_path = f"{self._file_path}.tmp"
        try:
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as file_handle:
                await file_handle.write(payload)
            os.replace(tmp_path, self._file_path)	# 🔀 Атомарно підміняємо
            logger.info("💾 Ваги збережено (%d запис(ів)) → %s", len(payload_obj), self._file_path)
        except Exception:
            logger.exception("❌ Не вдалося зберегти ваги у файл: %s", self._file_path)
            try:
                if os.path.exists(tmp_path):	# 🧹 Прибираємо tmp
                    os.remove(tmp_path)
            except Exception:
                pass

    async def flush(self) -> None:
        """🧽 Примусовий флаш у файл (без очікування debounce)."""
        async with self._lock:
            await self._flush_now_locked()  # 💾 Запис під lock
