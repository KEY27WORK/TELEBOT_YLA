""" 🧩 universal_product_parser.py — Універсальний парсер товарів YoungLA (US, EU, UK)

🔹 Клас `UniversalProductParser`:
- Визначає регіон (валюту) за URL
- Використовує `BaseParser` для асинхронного збору даних
- Повертає структуру з усіма полями товару

Використовує:
- Асинхронні методи з `BaseParser` для витягування інформації
"""

# 🔧 Системні
import re
import logging
import json
from typing import Dict, Any

# 🧠 Базовий парсер
from core.parsing.base_parser import BaseParser

from core.parsing.color_size_formatter import ColorSizeFormatter


class UniversalProductParser(BaseParser):
    """📦 Універсальний асинхронний парсер товарів з сайтів YoungLA.

    Парсить товари з регіонів:
    - US 🇺🇸 (www.youngla.com)
    - EU 🇪🇺 (eu.youngla.com)
    - UK 🇬🇧 (uk.youngla.com)
    """

    def __init__(self, url: str):
        """
        🔧 Ініціалізація з визначенням регіону (валюти).
        """
        self.url = url
        self.currency = self._detect_currency(url)
        super().__init__(url, currency_service=None)

    def _detect_currency(self, url: str) -> str:
        """
        🌍 Визначає валюту (регіон) за URL.

        :param url: Посилання на товар
        :return: "USD" / "EUR" / "GBP"
        """
        if re.match(r"^https://(www\.)?youngla\.com/", url):
            return "USD"
        elif "eu.youngla.com" in url:
            return "EUR"
        elif "uk.youngla.com" in url:
            return "GBP"
        else:
            raise ValueError(f"❌ Невідомий регіон: {url}")

    # --- 🎨 Обробка кольорів і розмірів ---

    async def format_colors_with_stock(self) -> str:
        """
        🎨 Формує текст із кольорами та доступністю розмірів.

        :return: Рядок для Telegram з форматованими даними
        """
        raw = await self.extract_colors_sizes()
        return ColorSizeFormatter.format_color_size_availability(raw)
    
    # --- 🛒 Перевірка наявності товару ---

    async def is_product_available(self) -> bool:
        """
        🛒 Перевіряє наявність товару на основі поля availability в JSON-LD.

        :return: True — товар є в наявності, False — немає
        """
        for script in self.soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product" and "offers" in data:
                    for offer in data["offers"]:
                        availability = offer.get("availability", "")
                        if "InStock" in availability:
                            return True
            except Exception as e:
                logging.warning(f"⚠️ JSON-LD parsing error: {e}")

        return False
    
    # --- 📦 Основний метод парсингу ---

    async def parse(self) -> Dict[str, Any]:
        """
        🧠 Основний метод парсингу.

        Повертає ключові поля товару:
        - title, price, currency, description
        - main_image, images, weight
        - colors_sizes (у форматі для Telegram)

        :return: Словник з усіма даними
        """
        if not await self.fetch_page():
            return {}

        # ⬇️ Витягуємо усі дані через BaseParser
        title = await self.extract_title()
        description = await self.extract_description()
        image_url = await self.extract_image()
        raw = await self.extract_colors_sizes()
        colors_sizes = await self.format_colors_sizes(raw)
        weight = await self.determine_weight(title, description, image_url)
        images = await self.extract_all_images()
        price = await self.extract_price()

        return {
            "title": title,
            "price": price,
            "currency": self.currency,
            "description": description,
            "main_image": image_url,
            "colors_sizes": colors_sizes,
            "images": images,
            "weight": weight
        }
