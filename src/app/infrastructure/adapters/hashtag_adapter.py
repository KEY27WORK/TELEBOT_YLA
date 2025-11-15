# 📬 app/infrastructure/content/adapters/hashtag_adapter.py
"""
📬 Адаптер узгоджує новий доменний `IHashtagGenerator` (повертає `Set[str]`)
з історичним кодом, який очікує одну строку з хештегами.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (немає)															# 🚫 Стандартні типи

# 🔠 Системні імпорти
import logging														# 🧾 Логи адаптера
from typing import Set												# 📐 Тип множини хештегів

# 🧩 Внутрішні модулі проєкту
from app.domain.content.interfaces import IHashtagGenerator			# 🧠 Новий доменний контракт
from app.domain.products.entities import ProductInfo				# 📦 Дані товару
from app.shared.utils.logger import LOG_NAME						# 🏷️ Узгоджені імена логів


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.content.hashtag_adapter")	# 🧾 Іменований логер


# ================================
# 🧩 АДАПТЕР ДЛЯ LEGACY API
# ================================
class HashtagGeneratorStringAdapter:
    """🧩 Обгортає `IHashtagGenerator`, щоб повернути рядок із хештегами."""

    def __init__(self, inner: IHashtagGenerator) -> None:
        self._inner = inner											# 🔁 Зберігаємо адаптований генератор
        logger.info("🏷️ HashtagGeneratorStringAdapter init done")	# 🪵 Лог ініціалізації

    async def generate(self, product_info: ProductInfo) -> str:
        """
        Args:
            product_info: Дані товару (title/description тощо).

        Returns:
            Строка з відсортованими хештегами або порожня строка.
        """
        logger.debug(
            "🏷️ hashtag_adapter.generate",
            extra={"title": getattr(product_info, "title", "N/A")},
        )															# 🪵 Діагностика виклику

        hashtags: Set[str] = await self._inner.generate(product_info)	# 🧠 Викликаємо новий контракт
        if not hashtags:											# 🚫 Немає результатів
            logger.info("🏷️ hashtag_adapter.empty", extra={"title": getattr(product_info, "title", "N/A")})
            return ""

        sorted_tags = sorted(hashtags)								# 🔤 Відсортовуємо для стабільності
        result = " ".join(sorted_tags)								# 🔗 Склеюємо через пробіл
        logger.debug("🏷️ hashtag_adapter.success", extra={"tags_count": len(sorted_tags)})
        return result												# ↩️ Рядок для legacy-коду


__all__ = ["HashtagGeneratorStringAdapter"]							# 📦 Експортований клас
