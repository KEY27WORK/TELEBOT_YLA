"""
🔹 Клас `JsonLdAvailabilityParser`:
- Витягує наявність кольорів і розмірів з JSON-LD блоків сторінки
- Якщо JSON-LD відсутній — парсить кольори з HTML (fallback)
- Конвертує нестандартні розміри у стандартні (наприклад, Shopify → M, L, XL...)
"""

# 📚 Стандартні бібліотеки
import json
import logging
import re

# 🌐 HTML парсер
from bs4 import BeautifulSoup


class JsonLdAvailabilityParser:
    """
    🧠 Парсер JSON-LD блоків для визначення доступності товарів (колір + розмір).
    Основний метод: `extract_color_size_availability(page_source)`
    """

    @staticmethod
    def extract_color_size_availability(page_source: str) -> dict:
        """
        📥 Головний метод: витягує доступність кольорів і розмірів з HTML (через JSON-LD).
        :param page_source: HTML-код сторінки
        :return: Словник у форматі {color: {size: bool}}
        """
        stock = {}
        try:
            soup = BeautifulSoup(page_source, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                data = json.loads(script.string or "{}")  # десеріалізація JSON
                # 🔍 Знаходимо блок Product з offers
                if (
                    isinstance(data, dict) and
                    data.get("@type") == "Product" and
                    "offers" in data
                ):
                    for offer in data["offers"]:
                        name = offer.get("name", "")
                        available = "InStock" in offer.get("availability", "")
                        # 🪓 Розбиваємо назву на колір і розмір (формат "Color / Size")
                        if " / " in name:
                            color, size = name.split(" / ")
                            size = JsonLdAvailabilityParser._map_size(size.strip())
                            stock.setdefault(color.strip(), {})[size] = available
        except Exception as e:
            logging.warning(f"⚠️ JSON-LD parsing error: {e}")

        # 🔁 Якщо JSON-LD не повернув даних — фолбек на HTML-кольори
        if not stock:
            stock = JsonLdAvailabilityParser._fallback_colors(page_source)
        return stock

    @staticmethod
    def _fallback_colors(page_source: str) -> dict:
        """
        🕵️‍♂️ Альтернативний метод: парсить кольори з HTML, якщо JSON-LD порожній.
        :param page_source: HTML-код сторінки
        :return: Словник {color: {}} — кольори без розмірів
        """
        soup = BeautifulSoup(page_source, "html.parser")
        colors = []
        # 🔍 Знаходимо блок зі свотчами кольорів (input name="Color")
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
        """
        🔄 Конвертація розміру з сирого формату (наприклад, Shopify) у стандартний.
        :param raw_size: Розмір (наприклад, "Medium", "XSmall")
        :return: Скорочений розмір типу "M", "XS", "XL" тощо
        """
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S",
            "Medium": "M", "Large": "L", "XLarge": "XL",
            "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        # 🧼 Залишаємо лише літери (видаляємо зайві символи)
        clean = re.sub(r'[^a-zA-Z]', '', raw_size)
        return size_mapping.get(clean, clean)
