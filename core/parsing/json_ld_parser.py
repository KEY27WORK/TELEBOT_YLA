"""
📦 json_ld_parser.py — легковесний утилітний парсер для JSON-LD блоків з HTML сторінки товарів YoungLA.

Відповідає за:
- Витяг кольорів і розмірів з JSON-LD
- Фолбек парсинг кольорів з HTML, якщо JSON-LD пустий
- Нормалізацію розмірів (Shopify → стандарт)
"""

import json
import logging
import re
from bs4 import BeautifulSoup


class JsonLdAvailabilityParser:
    @staticmethod
    def extract_color_size_availability(page_source: str) -> dict:
        stock = {}
        try:
            soup = BeautifulSoup(page_source, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                # Безопасно парсим JSON, если пустой или None — подставляем "{}"
                data = json.loads(script.string or "{}")
                if (
                    isinstance(data, dict) and
                    data.get("@type") == "Product" and
                    "offers" in data
                ):
                    for offer in data["offers"]:
                        name = offer.get("name", "")
                        available = "InStock" in offer.get("availability", "")
                        if " / " in name:
                            color, size = name.split(" / ")
                            size = JsonLdAvailabilityParser._map_size(size.strip())
                            stock.setdefault(color.strip(), {})[size] = available
        except Exception as e:
            logging.warning(f"⚠️ JSON-LD parsing error: {e}")

        # Фолбек, якщо JSON-LD пустий — парсимо кольори з HTML
        if not stock:
            stock = JsonLdAvailabilityParser._fallback_colors(page_source)
        return stock

    @staticmethod
    def _fallback_colors(page_source: str) -> dict:
        soup = BeautifulSoup(page_source, "html.parser")
        colors = []
        swatch_block = soup.find("div", class_="product-form__swatch color")
        if swatch_block:
            inputs = swatch_block.find_all("input", {"name": "Color"})
            colors = [
                input_tag.get("value", "").strip()
                for input_tag in inputs if input_tag.get("value")
            ]
        return {color: {} for color in colors}

    @staticmethod
    def _map_size(raw_size: str) -> str:
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        clean = re.sub(r'[^a-zA-Z]', '', raw_size)
        return size_mapping.get(clean, clean)