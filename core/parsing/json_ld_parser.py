"""
🔹 Клас `JsonLdAvailabilityParser`:
- Витягує наявність кольорів і розмірів з JSON-LD блоків сторінки
- Якщо JSON-LD відсутній — парсить кольори з HTML (fallback)
- Конвертує нестандартні розміри у стандартні (наприклад, Shopify → M, L, XL...)

Використовує:
- BeautifulSoup — для обробки HTML
- json — для десеріалізації скриптів типу application/ld+json
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
        📥 Головний метод: витягує доступність кольорів і розмірів з HTML (через JSON-LD)
        :param page_source: HTML-код сторінки
        :return: Словник у форматі {color: {size: bool}}
        """
        stock = {}
        try:
            soup = BeautifulSoup(page_source, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                # 📦 Парсим JSON або замінюємо на пустий об'єкт, якщо None
                data = json.loads(script.string or "{}")

                # 🔍 Шукаємо блок Product з offers
                if (
                    isinstance(data, dict) and
                    data.get("@type") == "Product" and
                    "offers" in data
                ):
                    for offer in data["offers"]:
                        name = offer.get("name", "")
                        available = "InStock" in offer.get("availability", "")

                        # 🪓 Розбиваємо назву на колір + розмір, якщо у форматі "Color / Size"
                        if " / " in name:
                            color, size = name.split(" / ")
                            size = JsonLdAvailabilityParser._map_size(size.strip())
                            stock.setdefault(color.strip(), {})[size] = available

        except Exception as e:
            # ⚠️ Лог помилки, якщо парсинг JSON-LD не вдався
            logging.warning(f"⚠️ JSON-LD parsing error: {e}")

        # 🔁 Якщо JSON-LD не повернув нічого — фолбек на HTML-кольори
        if not stock:
            stock = JsonLdAvailabilityParser._fallback_colors(page_source)

        return stock

    @staticmethod
    def _fallback_colors(page_source: str) -> dict:
        """
        🕵️‍♂️ Альтернативний метод: парсить кольори з HTML, якщо JSON-LD пустий
        :param page_source: HTML-код сторінки
        :return: Словник {color: {}} — без розмірів
        """
        soup = BeautifulSoup(page_source, "html.parser")
        colors = []

        # 🔍 Знаходимо блок зі свотчами кольорів (радіо-input із name=Color)
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
        🔄 Конвертація розміру з сирого формату (наприклад, Shopify) у стандартний
        :param raw_size: Рядок, типу "Medium", "XSmall"
        :return: Короткий розмір типу "M", "XS", "XL" тощо
        """
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        # 🧼 Чистимо розмір — залишаємо лише літери
        clean = re.sub(r'[^a-zA-Z]', '', raw_size)
        return size_mapping.get(clean, clean)
