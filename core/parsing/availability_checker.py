"""
📦 availability_checker.py — Перевірка базової доступності товару в регіонах YoungLA.

🔹 Клас:
- `AvailabilityChecker` — перевіряє наявність товару (без деталізації розмірів/кольорів)

Використовує:
- BaseParser для парсингу
- asyncio для паралельного виконання
- logging для діагностики
"""

# 📦 Стандартні імпорти
import asyncio
import logging

# 🧠 Парсер
from core.parsing.base_parser import BaseParser


class AvailabilityChecker:
    """
    📦 Клас для перевірки базової наявності товару по основних регіонах YoungLA (US, EU, UK).

    ▪️ Дає загальну відповідь — чи доступний товар в кожному регіоні.
    ▪️ Не перевіряє кольори та розміри — лише глобальну доступність.
    """

    REGIONS = {
        "🇺🇸": "https://www.youngla.com",
        "🇪🇺": "https://eu.youngla.com",
        "🇬🇧": "https://uk.youngla.com"
    }

    @staticmethod
    async def check(product_path: str) -> str:
        """
        🔍 Основна перевірка доступності по всіх регіонах.

        :param product_path: Шлях до товару (наприклад: /products/name-id)
        :return: Строка для Telegram з емодзі-прапорами і статусами.
        """
        tasks = [
            AvailabilityChecker._check_region(flag, f"{url}{product_path}")
            for flag, url in AvailabilityChecker.REGIONS.items()
        ]

        results = await asyncio.gather(*tasks)
        return "\n".join(results) + "\n🇺🇦 - ❌"

    @staticmethod
    async def _check_region(region_flag: str, url: str) -> str:
        """
        📦 Перевірка одного окремого регіону.

        :param region_flag: Емодзі регіону (🇺🇸/🇪🇺/🇬🇧)
        :param url: Повний URL до товару в конкретному регіоні
        :return: Строка формату «🇺🇸 - ✅ / ❌»
        """
        try:
            parser = BaseParser(url, enable_progress=False)
            await parser.fetch_page()
            available = await parser.is_product_available()
            logging.info(f"🌍 Перевірка: {region_flag} — {'✅' if available else '❌'}")
            return f"{region_flag} - {'✅' if available else '❌'}"
        except Exception as e:
            logging.error(f"❌ Помилка в {region_flag}: {e}")
            return f"{region_flag} - ❌ (помилка)"