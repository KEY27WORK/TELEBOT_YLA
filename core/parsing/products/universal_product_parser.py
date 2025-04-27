""" 🧩 universal_product_parser.py — Універсальний парсер товарів YoungLA (US, EU, UK)

🔹 Клас `UniversalProductParser`:
- Визначає регіон (валюту) за URL
- Використовує BaseParser для асинхронного збору даних
- Повертає структуру з усіма полями товару

Використовує:
- Асинхронні методи з `BaseParser` для витягування інформації
"""

import logging
from typing import Dict, Any
from core.parsing.base_parser import BaseParser
import re


class UniversalProductParser(BaseParser):
    """
    📦 Універсальний асинхронний парсер товарів з сайтів YoungLA:
    - Працює з регіонами US, EU, UK
    - Визначає валюту автоматично
    - Парсить усі ключові дані: назва, опис, зображення, кольори/розміри, ціна, вага
    """

    def __init__(self, url: str):
        self.url = url
        self.currency = self._detect_currency(url)
        # 🧱 Ініціалізуємо BaseParser без currency_service (не використовується)
        super().__init__(url, currency_service=None)


    def _detect_currency(self, url: str) -> str:
        """
        🌍 Визначає валюту (регіон) за URL:
        - www.youngla.com → USD
        - eu.youngla.com → EUR
        - uk.youngla.com → GBP
        """
        if re.match(r"^https://(www\.)?youngla\.com/", url):
            return "USD"
        elif "eu.youngla.com" in url:
            return "EUR"
        elif "uk.youngla.com" in url:
            return "GBP"
        else:
            raise ValueError(f"❌ Невідомий регіон: {url}")

    

    async def parse(self) -> Dict[str, Any]:
        """
        🧠 Основний метод парсингу.
        Повертає всі ключові дані товару:
        - title, description, image_url, colors_sizes, weight, images, price, currency
        """
        if not await self.fetch_page():
            return {}

        # 🔍 Витягуємо всі поля через BaseParser
        title = await self.extract_title()
        description = await self.extract_description()
        image_url = await self.extract_image()
        colors_sizes = await self.extract_colors_sizes()
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
