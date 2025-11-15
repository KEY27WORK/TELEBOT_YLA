# 🌍 app/infrastructure/web/__init__.py
"""
🌍 Інфраструктурний модуль для завантаження HTML сторінок через Playwright.

🔹 Експортує реалізацію `WebDriverService`, сумісну з `IWebClient`.
🔹 Використовується парсерами для стабільного та асинхронного отримання HTML.
"""

from __future__ import annotations

# 🧭 Основний сервіс
from .webdriver_service import WebDriverService

__all__ = ["WebDriverService"]
