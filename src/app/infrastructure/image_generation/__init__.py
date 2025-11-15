# 🎨 app/infrastructure/image_generation/__init__.py
"""
🎨 Сервіси для генерації/опрацювання зображень.

🔹 `FontService` — менеджер шрифтів та їх кешування для PIL/Canvas.
"""

from __future__ import annotations

from .font_service import FontService	# ✍️ Головний сервіс шрифтів

__all__ = ["FontService"]	# 📦 Публічний експорт пакета
