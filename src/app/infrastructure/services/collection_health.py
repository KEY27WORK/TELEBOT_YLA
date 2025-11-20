# 🩺 app/infrastructure/services/collection_health.py
"""
🩺 CollectionHealthSummary — прості показники здоров'я поточної колекції.

🔹 Накопичуємо кількість успішних товарів, ALT-фолбеків та невдалих айтемів.
🔹 Використовується під час обробки колекції, щоб логувати та показувати короткий звіт.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CollectionHealthSummary:
    """🩺 Метрики стану колекції для звітності."""

    total: int = 0
    ok: int = 0
    alt_fallback: int = 0
    failed: int = 0

    def register_ok(self, alt_fallback_used: bool) -> None:
        """🔢 Обновити, якщо продукт оброблено успішно."""
        self.total += 1
        if alt_fallback_used:
            self.alt_fallback += 1
        else:
            self.ok += 1

    def register_failed(self) -> None:
        """🚨 Обновити, якщо продукт не вдався."""
        self.total += 1
        self.failed += 1


__all__ = ["CollectionHealthSummary"]
