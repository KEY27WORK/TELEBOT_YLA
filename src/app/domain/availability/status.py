# 🧩 app/domain/availability/status.py
"""
🧩 status.py — Перечисление статусов наличия товара.

Зачем Enum?
- В отличие от Optional[bool], None не схлопывается в False (bool(None) == False).
- Типобезопасность и понятная семантика: YES / NO / UNKNOWN.
- Удобные утилиты для конвертаций, сравнения и агрегации статусов.
"""

from __future__ import annotations

# 🔠 Стандартні імпорти
import logging                                                        # 🧾 Логування роботи статусів
from enum import Enum, unique                                         # 🧱 Побудова enum з гарантією унікальності
from typing import Iterable, Optional                                 # 🧰 Типи для утиліт

# 🧩 Внутрішні модулі
from app.shared.utils.logger import LOG_NAME                          # 🏷️ Глобальний префікс логера


# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
MODULE_LOGGER_NAME: str = f"{LOG_NAME}.domain.availability.status"   # 🏷️ Іменований префікс
logger = logging.getLogger(MODULE_LOGGER_NAME)                        # 🧾 Модульний логер
logger.debug("🧩 availability.status імпортовано")                    # 🚀 Фіксуємо ініціалізацію


@unique
class AvailabilityStatus(str, Enum):
    """Трёхсостояний статус наличия."""
    YES = "yes"          # ✅ В наличии (товар доступний для купівлі)
    NO = "no"            # ❌ Немає в наявності (обмеження для всіх регіонів)
    UNKNOWN = "unknown"  # ❔ Невідомо (немає даних/сталася помилка)

    # ---------- БАЗОВЫЕ УДОБСТВА ----------
    def __str__(self) -> str:  # Для красивого вывода и сериализации
        logger.debug("🔁 __str__ викликано | status=%s", self.value)   # 🧾 Трасуємо перетворення у str
        return self.value                                             # 📤 Повертаємо канонічне текстове значення

    @property
    def is_available(self) -> bool:
        """True, если статус — YES."""
        result = self is AvailabilityStatus.YES                       # ✅ YES = True, решта = False
        logger.debug("✅ is_available | status=%s result=%s", self.value, result)  # 🧾 Для аудиту логіки UI
        return result

    def emoji(self) -> str:
        """Человеко‑понятная пиктограмма статуса."""
        if self is AvailabilityStatus.YES:
            emoji_value = "✅"
        elif self is AvailabilityStatus.NO:
            emoji_value = "🚫"
        else:
            emoji_value = "❔"                                           # UNKNOWN
        logger.debug("😀 emoji | status=%s emoji=%s", self.value, emoji_value)    # 🧾 Пояснюємо відображення в UI
        return emoji_value                                                      # 📤 Повертаємо обрану піктограму

    def to_bool(self) -> Optional[bool]:
        """
        Конвертирует статус в булево представление:
          YES -> True, NO -> False, UNKNOWN -> None.
        """
        if self is AvailabilityStatus.YES:
            logger.debug("🔄 to_bool YES -> True")
            return True
        if self is AvailabilityStatus.NO:
            logger.debug("🔄 to_bool NO -> False")
            return False
        logger.debug("🔄 to_bool UNKNOWN -> None")                     # 🔁 UNKNOWN зберігаємо як None
        return None                                                   # 📤 Повертаємо тристанове значення

    # ---------- КЛАССОВЫЕ УТИЛИТЫ ----------
    @classmethod
    def from_bool(cls, value: Optional[bool]) -> "AvailabilityStatus":
        """True -> YES, False -> NO, None -> UNKNOWN."""
        if value is True:                                             # ✅ Позитивне значення → YES
            logger.debug("🧭 from_bool True -> YES")
            return cls.YES
        if value is False:                                            # ❌ False прямо мапимо на NO
            logger.debug("🧭 from_bool False -> NO")
            return cls.NO
        logger.debug("🧭 from_bool None/other -> UNKNOWN")            # ❔ Null/інші випадки → UNKNOWN
        return cls.UNKNOWN                                            # 📤 Повертаємо дефолт

    @classmethod
    def from_str(cls, value: Optional[str]) -> "AvailabilityStatus":
        """
        Парсинг из строки (безопасно, регистронезависимо).
        Понимает: "yes"/"true"/"1"/"y"/"available", "no"/"false"/"0"/"n"/"unavailable", остальное -> UNKNOWN.
        """
        if value is None:
            logger.debug("🔤 from_str None -> UNKNOWN")
            return cls.UNKNOWN
        s = value.strip().lower()                                      # ✂️ Приводимо до спільного формату
        if s in {"yes", "true", "1", "y", "available", "in_stock", "ok"}:  # ✅ Традиційні позитивні позначення
            logger.debug("🔤 from_str %r -> YES", value)
            return cls.YES
        if s in {"no", "false", "0", "n", "unavailable", "out_of_stock"}:  # 🚫 Список явних відмов
            logger.debug("🔤 from_str %r -> NO", value)
            return cls.NO
        if s in {"unknown", "?", "na", "n/a", "none", ""}:                 # ❔ Значення, що явно означають невідомо
            logger.debug("🔤 from_str %r -> UNKNOWN (explicit set)", value)
            return cls.UNKNOWN
        logger.debug("🔤 from_str %r -> UNKNOWN (fallback)", value)        # 🕳️ Будь-яке інше значення → UNKNOWN
        return cls.UNKNOWN                                                # 📤 Повертаємо дефолт

    @classmethod
    def merge(cls, a: "AvailabilityStatus", b: "AvailabilityStatus") -> "AvailabilityStatus":
        """
        Объединение двух статусов (приоритеты):
          1) если есть хотя бы один YES → YES
          2) иначе если есть хотя бы один NO → NO
          3) иначе → UNKNOWN
        """
        if a is cls.YES or b is cls.YES:                               # ✅ Найменший опір: якщо щось доступно — беремо YES
            logger.debug("➕ merge YES detected | a=%s b=%s", a, b)
            return cls.YES
        if a is cls.NO or b is cls.NO:                                 # 🚫 Інакше — якщо хоч десь NO, це важливіше за UNKNOWN
            logger.debug("➕ merge NO detected | a=%s b=%s", a, b)
            return cls.NO
        logger.debug("➕ merge -> UNKNOWN | a=%s b=%s", a, b)           # ❔ Обидва UNKNOWN → результат UNKNOWN
        return cls.UNKNOWN

    @classmethod
    def combine(cls, statuses: Iterable["AvailabilityStatus"]) -> "AvailabilityStatus":
        """
        Агрегирует произвольную последовательность статусов по тем же правилам, что и merge.
        Удобно для сводки по множеству регионов.
        """
        seen_no = False                                                # 🚩 Запам'ятовуємо, чи зустрічали хоч один NO
        for st in statuses:                                           # 🔁 Проходимо всі вхідні статуси
            logger.debug("🔗 combine iter | status=%s", st)           # 🧾 Логуємо кожну ітерацію
            if st is cls.YES:                                        # ✅ YES миттєво завершує агрегацію
                logger.debug("🔗 combine -> YES")
                return cls.YES
            if st is cls.NO:                                         # 🚫 Фіксуємо, що NO траплявся (але продовжуємо)
                seen_no = True
        result = cls.NO if seen_no else cls.UNKNOWN                  # 🧮 Після проходу вирішуємо: NO > UNKNOWN
        logger.debug("🔗 combine завершено | result=%s", result)      # 🧾 Підсумковий результат
        return result                                                # 📤 Повертаємо агрегований статус

    @classmethod
    def priority(cls, status: "AvailabilityStatus") -> int:
        """
        Числовой приоритет для сортировок/сравнений (меньше — «лучше»):
          YES(0) < NO(1) < UNKNOWN(2)
        """
        if status is cls.YES:                                          # ✅ Найвищий пріоритет
            logger.debug("📊 priority YES -> 0")
            return 0
        if status is cls.NO:                                           # 🚫 Середній пріоритет
            logger.debug("📊 priority NO -> 1")
            return 1
        logger.debug("📊 priority UNKNOWN -> 2")                       # ❔ Низький пріоритет — невизначеність
        return 2  # UNKNOWN


# ==============================
# 📦 ПУБЛИЧНЫЙ API МОДУЛЯ
# ==============================
__all__ = ["AvailabilityStatus"]
logger.debug("🔓 __all__ оголошено: %s", __all__)
