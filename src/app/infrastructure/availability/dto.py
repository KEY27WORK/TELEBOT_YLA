# 📦 app/infrastructure/availability/dto.py
"""
📦 DTO для текстових звітів Availability (публічний + адмінський).

🔹 `AvailabilityReports` інкапсулює обидва рядки, зручні утиліти (`is_blank`, `to_dict`, ...).  
🔹 Immutable (frozen) + slots → легша серіалізація й кешування.  
🔹 Використовується Formatter/ReportBuilder для передачі у Telegram.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логи DTO (виклики утиліт)
from dataclasses import dataclass                                   # 📦 Створення DTO
from typing import Dict, Tuple                                      # 📐 Типи зручних методів

logger = logging.getLogger(__name__)                                # 🧾 Локальний логер DTO


# ================================
# 📊 DTO ЗВІТІВ
# ================================
@dataclass(frozen=True, slots=True)
class AvailabilityReports:
    """📊 Сховище публічного й адмінського звітів."""

    public_report: str                                               # 📄 Текст для користувача
    admin_report: str                                                # 🔒 Розширений звіт

    def is_blank(self) -> bool:
        """Перевіряє, що обидва звіти порожні (після trim)."""
        blank_public = not (self.public_report or "").strip()        # 🧼 Чи порожній публічний текст
        blank_admin = not (self.admin_report or "").strip()          # 🧼 Чи порожній адмінський текст
        logger.debug("📦 is_blank? public=%s admin=%s", blank_public, blank_admin)
        return blank_public and blank_admin

    def to_tuple(self) -> Tuple[str, str]:
        """Повертає `(public, admin)` для зручної передачі в месенджер."""
        logger.debug("📦 to_tuple виклик")
        return self.public_report, self.admin_report

    def to_dict(self) -> Dict[str, str]:
        """Серіалізація у словник (логування/кеш/тести)."""
        payload = {"public_report": self.public_report, "admin_report": self.admin_report}  # 📄 Готова структура
        logger.debug("📦 to_dict payload=%s", payload)
        return payload

    def with_prefix(self, prefix: str) -> "AvailabilityReports":
        """Повертає новий DTO з доданим префіксом до обох звітів."""
        p = f"{prefix}{self.public_report}" if prefix else self.public_report  # 📌 Додаємо префікс до public
        a = f"{prefix}{self.admin_report}" if prefix else self.admin_report    # 📌 ...і до admin
        logger.debug("📦 with_prefix='%s'", prefix)
        return AvailabilityReports(public_report=p, admin_report=a)

    def __str__(self) -> str:
        """Створює коротке string-представлення (публічний звіт)."""
        preview = (self.public_report or "").splitlines()[0:2]       # 👀 Перші рядки для дебагу
        logger.debug("📦 __str__ preview=%s", preview)
        return self.public_report


__all__ = ["AvailabilityReports"]
