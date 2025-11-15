# 🧾 app/infrastructure/parsers/extractors/__init__.py
"""
🧾 Міксини/екстрактори для витягування даних із DOM та JSON-LD.

🔹 `Selectors`, `_ConfigSnapshot` — базова конфігурація селекторів.
🔹 `JsonLdMixin`, `ImagesMixin`, `DescriptionMixin` — спеціалізовані екстрактори.
"""

from __future__ import annotations

from .base import Selectors, _ConfigSnapshot												# 🧱 Базові селектори та snapshot
from .description import DescriptionMixin													# 📝 Витяг опису
from .images import ImagesMixin															# 🖼️ Витяг зображень
from .json_ld import JsonLdMixin															# 📄 Витяг із JSON-LD

__all__ = [
    "Selectors",																			# 🧱 Конфіг селекторів
    "_ConfigSnapshot",																	# 🧾 Snapshot селекторів
    "DescriptionMixin",																	# 📝 Екстрактор опису
    "ImagesMixin",																		# 🖼️ Екстрактор зображень
    "JsonLdMixin",																		# 📄 Екстрактор JSON-LD
]
