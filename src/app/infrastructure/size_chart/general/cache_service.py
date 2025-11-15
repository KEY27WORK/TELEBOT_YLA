# 💾 app/infrastructure/size_chart/general/cache_service.py
"""
💾 Кеш PNG для універсальних таблиць YoungLA.

🔹 Зберігає по одному згенерованому PNG на кожен variant (`men`, `women`).
🔹 Дозволяє швидко повертати вже готові таблиці без повторного OCR/AI.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки — відсутні

# 🔠 Системні імпорти
import logging																# 🧾 Логування кешу
import shutil																# 📦 Копіювання файлів
from pathlib import Path													# 🛤️ Шляхи
from typing import Optional												# 🧰 Типізація публічного API

# 🧩 Внутрішні модулі проєкту
from .types import GeneralChartVariant										# 🏷️ Перелік варіантів

logger = logging.getLogger(__name__)										# 🧾 Локальний логер


# ================================
# 💾 КЕШ PNG
# ================================
class GeneralChartCache:
    """💾 Керує збереженими PNG для універсальних таблиць."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()							# 🛤️ Каталог кешу
        self.root_dir.mkdir(parents=True, exist_ok=True)
        logger.info("💾 Ініціалізовано кеш загальних таблиць у %s", self.root_dir)

    def get_cached_path(self, variant: GeneralChartVariant) -> Optional[str]:
        """📥 Повертає шлях до кешованої таблиці або None."""
        cache_path = self._path_for_variant(variant)						# 🛤️ Обчислюємо шлях
        if cache_path.exists():
            logger.debug("💾 Cache hit: %s (%s)", variant.value, cache_path)
            return str(cache_path)
        logger.debug("💾 Cache miss: %s (%s)", variant.value, cache_path)
        return None

    def store_result(self, variant: GeneralChartVariant, result_path: str) -> str:
        """📤 Зберігає нову таблицю у кеш і повертає шлях."""
        cache_path = self._path_for_variant(variant)						# 🛤️ Кінцевий файл
        shutil.copyfile(result_path, cache_path)							# 📦 Копіюємо png
        logger.info("💾 Cache update: %s → %s", result_path, cache_path)
        return str(cache_path)

    def _path_for_variant(self, variant: GeneralChartVariant) -> Path:
        """🛤️ Формує повний шлях для men/women PNG."""
        filename = f"{variant.value}.png"									# 🏷️ Імʼя файлу
        return self.root_dir / filename									# 🔗 Абсолютний шлях


__all__ = ["GeneralChartCache"]											# 📦 API модуля
