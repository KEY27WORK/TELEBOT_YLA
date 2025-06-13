"""
📦 json_ld_parser.py — парсер JSON-LD блоків з HTML сторінки товарів YoungLA.

🔹 Клас:
- `JsonLdAvailabilityParser` — легковесний утилітний парсер для витягування кольорів і розмірів з JSON-LD.

Використовується:
- Всередині AvailabilityAggregator
- Для обробки даних по кожному регіону окремо.
"""

# 📦 Стандартні
import json
import logging
import re

# 🌐 HTML парсинг
from bs4 import BeautifulSoup


class JsonLdAvailabilityParser:
    """
    🔍 Парсер JSON-LD із HTML сторінки:
    - Витягує кольори та розміри із внутрішнього скрипту
    - Працює швидко та ефективно при наявності валідного JSON-LD
    """

    @staticmethod
    def extract_color_size_availability(page_source: str) -> dict:
        """
        📊 Основний метод витягування карти наявності кольорів та розмірів.

        :param page_source: HTML сторінки як строка.
        :return: Словник виду: {color: {size: доступність (bool)}}
        """
        soup = BeautifulSoup(page_source, "html.parser")
        stock = {}

        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)

                if isinstance(data, dict) and data.get("@type") == "Product" and "offers" in data:
                    for offer in data["offers"]:
                        name = offer.get("name", "")
                        available = "InStock" in offer.get("availability", "")
                        if " / " in name:
                            color, size = name.split(" / ")
                            color = color.strip()
                            size = JsonLdAvailabilityParser._map_size(size.strip())
                            stock.setdefault(color, {}).update({size: available})
            except Exception as e:
                logging.warning(f"⚠️ JSON-LD parsing error: {e}")
        return stock

    @staticmethod
    def _map_size(raw_size: str) -> str:
        """
        🔄 Нормалізація розмірів з Shopify форматів до стандартних.

        :param raw_size: Розмір у сирому вигляді (наприклад 'XLarge').
        :return: Нормалізований розмір (наприклад 'XL').
        """
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        clean = re.sub(r'[^a-zA-Z]', '', raw_size)
        return size_mapping.get(clean, clean)