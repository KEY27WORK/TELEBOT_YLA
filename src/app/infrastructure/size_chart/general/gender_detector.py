# 🚻 app/infrastructure/size_chart/general/gender_detector.py
"""
🚻 Детектор статі товару на основі YoungLA HTML/SKU.

🔹 Витягує перший зустрінутий SKU з JSON-LD/inline-скриптів.
🔹 За префіксом `W`/`w` визначає жіночі товари (чоловічі — цифри/інші літери).
🔹 Дає fallback `UNKNOWN`, якщо html порожній або не містить SKU.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки — відсутні

# 🔠 Системні імпорти
import logging																# 🧾 Діагностика визначення
import re																	# 🔍 Пошук SKU у HTML
from typing import Iterator												# 📚 Ітерація значень

# 🧩 Внутрішні модулі проєкту
from .types import ProductGender											# 🚻 Перелік статей

logger = logging.getLogger(__name__)										# 🧾 Локальний логер


# ================================
# 🚻 ДЕТЕКТОР
# ================================
class YoungLAProductGenderDetector:
    """🚻 Визначає стать YoungLA-продукта на основі артикулу."""

    _SKU_PATTERN = re.compile(r'"sku"\s*:\s*"([^"]+)"', re.IGNORECASE)		# 🔎 JSON-LD / inlined SKU
    _HANDLE_PATTERN = re.compile(r'"product"\s*:\s*"([^"]+)"', re.IGNORECASE)	# 🏷️ Handle як fallback

    def detect(self, page_source: str) -> ProductGender:
        """
        🚻 Визначає стать (men/women) за першим знайденим SKU/handle.

        Args:
            page_source: HTML сторінки YoungLA.
        """
        if not page_source or not page_source.strip():						# 🚫 Порожній HTML
            logger.debug("🚻 Детектор отримав порожній page_source")
            return ProductGender.UNKNOWN

        logger.debug("🚻 Аналізуємо HTML (довжина=%d символів).", len(page_source))
        fallback: ProductGender = ProductGender.UNKNOWN					# 🪢 Зберігаємо перший валідний кандидат
        for candidate in self._iter_candidates(page_source):				# 🔁 Пошук усіх можливих значень
            first_char = self._extract_first_symbol(candidate)				# 🔤 Беремо перший алфанумеричний символ
            if not first_char:
                logger.debug("🚻 Пропускаємо кандидат без алфанумеричних символів: '%s'", candidate)
                continue													# ⏭️ Пропускаємо сміття
            if first_char.lower() == "w":									# 👩‍🦰 SKU починається з W → жінки
                logger.debug("🚻 SKU='%s' визначено як WOMEN", candidate)
                return ProductGender.WOMEN
            if fallback is ProductGender.UNKNOWN:							# 🧔‍♂️ Пам'ятаємо перший не-W кандидат
                fallback = ProductGender.MEN
                logger.debug("🚻 SKU='%s' кандидує як MEN (очікую жінок)", candidate)

        if fallback is not ProductGender.UNKNOWN:							# 🧔‍♂️ Всі кандидати були чоловічими
            return fallback

        logger.debug("🚻 SKU не знайдено, повертаю UNKNOWN")
        return ProductGender.UNKNOWN										# ❔ Фолбек

    def _iter_candidates(self, page_source: str) -> Iterator[str]:
        """🔍 Повертає усі можливі SKU/handle з HTML."""
        count = 0
        for match in self._SKU_PATTERN.finditer(page_source):				# 🔁 JSON-LD SKU
            value = match.group(1).strip()
            if value:
                count += 1
                yield value												# 📤 Повертаємо перший артикул
        for match in self._HANDLE_PATTERN.finditer(page_source):			# 🔁 Fallback на handle
            value = match.group(1).strip()
            if value:
                count += 1
                yield value
        logger.debug("🚻 Кандидатів SKU/handle знайдено: %d", count)

    def _extract_first_symbol(self, raw: str) -> str:
        """🔤 Повертає перший алфанумеричний символ з рядка."""
        for char in raw:
            if char.isalnum():
                return char
        return ""															# 🚫 Не знайдено символів


__all__ = ["ProductGender", "YoungLAProductGenderDetector"]				# 📦 Експортовані сутності
