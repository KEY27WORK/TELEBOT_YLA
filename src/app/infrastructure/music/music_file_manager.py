# 🎼 app/infrastructure/music/music_file_manager.py
"""
🎼 MusicFileManager — керує локальним кешем mp3-файлів.

🔹 Отримує шлях до вже збережених треків.
🔹 Очищує кеш асинхронно у фоні.
🔹 Нормалізує назви файлів та гарантує наявність директорії.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio	# ⏱️ Виносимо блокувальні операції в thread pool
import glob	# 🔍 Пошук mp3-файлів у кеші
import logging	# 🧾 Логування операцій файлового шару
import os	# 📁 Робота з файловою системою
import re	# 🧼 Нормалізація імен файлів
from typing import Optional	# 🧰 Анотації

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService
from app.domain.music.interfaces import IMusicFileManager, RecommendedTrack
from app.shared.utils.logger import LOG_NAME

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)	# 🧾 Використовуємо загальний логер застосунку


class MusicFileManager(IMusicFileManager):
    """🎧 Відповідає лише за файлові операції без завантажень/мережі."""

    def __init__(self, config: ConfigService) -> None:
        """⚙️ Зберігає шлях до кешу та створює директорію, якщо вона відсутня."""
        cache_dir = str(config.get("files.music_cache", "music_cache"))	# 🗂️ Шлях із конфігурації
        self._cache_dir: str = cache_dir	# 🧾 Зберігаємо як атрибут
        os.makedirs(self._cache_dir, exist_ok=True)	# 🧱 Гарантуємо існування директорії
        logger.debug("🎧 Music cache directory готовий: %s", self._cache_dir)	# 🪵 Діагностика

    # ================================
    # 📣 ПУБЛІЧНИЙ API
    # ================================
    def get_cached_path(self, track: RecommendedTrack) -> Optional[str]:
        """
        Повертає абсолютний шлях до mp3, якщо файл уже є в кеші.

        Args:
            track: RecommendedTrack (artist + title)
        """
        file_path = self._generate_path(track.display_name)	# 📄 Формуємо шлях
        if os.path.exists(file_path):	# ✅ Кеш-хіт
            logger.debug("🎧 Кеш-хіт для треку '%s': %s", track.display_name, file_path)
            return file_path
        logger.debug("🎧 Кеш-промах для треку '%s'", track.display_name)	# ❌ Немає файлу
        return None

    async def clear_cache(self) -> None:
        """🧹 Асинхронне очищення кешу у фоні."""
        await asyncio.to_thread(self._blocking_clear_cache)	# 🔁 Виносимо блокувальну операцію

    # ================================
    # ⚙️ ВНУТРІШНІ МЕТОДИ
    # ================================
    def _blocking_clear_cache(self) -> None:
        """🧽 Видаляє всі mp3 з кешу (блокувальна операція)."""
        logger.info("🧹 Очищення музичного кешу…")	# 🪵 Початок операції
        pattern = os.path.join(self._cache_dir, "*.mp3")	# 🗂️ Маска для mp3
        for filepath in glob.glob(pattern):	# 🔁 Перебираємо всі файли
            try:
                os.remove(filepath)	# ❌ Видаляємо файл
                logger.debug("🧺 Видалено з кешу: %s", filepath)	# 🪵 Успіх
            except Exception as exc:  # noqa: BLE001
                logger.warning("⚠️ Не вдалося видалити %s: %s", filepath, exc)	# ⚠️ Попередження

    def _generate_path(self, name: str) -> str:
        """📁 Формує детермінований шлях до mp3 у кеші."""
        clean = self._clean_track_name(name)	# 🧼 Нормалізоване імʼя файлу
        return os.path.join(self._cache_dir, f"{clean}.mp3")	# 📎 Повний шлях

    @staticmethod
    def _clean_track_name(name: str) -> str:
        """🧼 Фільтрує назву треку: дозволяє [a-zA-Z0-9] + пробіли + -_()[]."""
        filtered = re.sub(r"[^\w\s\-\(\)\[\]]", "", name or "").strip()	# 🧹 Видаляємо заборонені символи
        return re.sub(r"\s+", "_", filtered)	# 🔁 Замінюємо пробіли на підкреслення


__all__ = ["MusicFileManager"]	# 📦 Експортований інтерфейс модуля
