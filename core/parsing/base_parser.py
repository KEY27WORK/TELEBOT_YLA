""" 🧠 base_parser.py — Базовий клас для парсингу сторінок товарів YoungLA.

🔹 Клас `BaseParser`:
- Самостійно визначає валюту по URL
- Асинхронно завантажує HTML через Playwright
- Витягує ціну, опис, зображення, кольори, розміри, наявність
- Формує форматований словник для Telegram
"""

# 📦 Стандартні
import re
import time
import json
import logging
import asyncio
from typing import Dict, Any, Optional

# 🌐 Парсинг HTML
from bs4 import BeautifulSoup

# 🧱 Сервіси
from core.webdriver.webdriver_service import WebDriverService
from core.config.config_service import ConfigService
from bot.content.translator import TranslatorService
from core.parsing.color_size_formatter import ColorSizeFormatter


class BaseParser:
    def __init__(self, url: str):
        self.url = url
        self.page_source: Optional[str] = None
        self.soup: Optional[BeautifulSoup] = None
        self.config = ConfigService()
        self.translator = TranslatorService()
        self._currency = self._detect_currency(url)

    def _detect_currency(self, url: str) -> str:
        if ".com" in url and "eu." not in url and "uk." not in url:
            return "USD"
        elif "eu." in url:
            return "EUR"
        elif "uk." in url:
            return "GBP"
        else:
            raise ValueError(f"❌ Невідомий регіон: {url}")

    async def fetch_page(self, retries: int = 5) -> bool:
        self.page_source = None
        start_time = time.time()

        for attempt in range(1, retries + 1):
            self.page_source = await WebDriverService().fetch_page_source(self.url)
            if self.page_source:
                self.soup = BeautifulSoup(self.page_source, "html.parser")
                logging.info(f"✅ Сторінку завантажено: {self.url}")
                logging.info(f"⏳ Час завантаження: {time.time() - start_time:.2f} сек.")
                return True

            logging.warning(f"🔄 Спроба {attempt}: не вдалося завантажити сторінку...")
            await asyncio.sleep(2)

        logging.error(f"❌ Не вдалося завантажити сторінку: {self.url}")
        return False

    # --- Витягування даних ---

    async def extract_title(self) -> str:
        title_tag = self.soup.find("h1")
        return title_tag.text.strip() if title_tag else "Без назви"

    async def extract_price(self) -> float:
        meta = self.soup.find("meta", {"property": "product:price:amount"})
        if meta:
            try:
                return float(meta["content"].replace(",", "."))
            except ValueError:
                logging.warning(f"⚠️ Неможливо розпізнати ціну: {meta['content']}")
        return 0.0

    async def extract_description(self) -> str:
        meta = self.soup.find("meta", {"name": "twitter:description"})
        return meta["content"] if meta else "Опис відсутній"

    async def extract_image(self) -> str:
        meta = self.soup.find("meta", {"property": "og:image"})
        return meta["content"] if meta else "Зображення відсутнє"

    async def extract_all_images(self) -> list[str]:
        images = []
        gallery = self.soup.select_one(".product-gallery__thumbnail-list")
        if gallery:
            for img in gallery.select("button img[src]"):
                url = img["src"]
                if url.startswith("//"):
                    url = "https:" + url
                images.append(url)
                logging.info(f"📸 Знайдено зображення: {url}")
        return images

    async def extract_colors_from_html(self) -> list[str]:
        colors = []
        swatch_block = self.soup.find("div", class_="product-form__swatch color")
        if swatch_block:
            inputs = swatch_block.find_all("input", {"name": "Color"})
            for input_tag in inputs:
                color_name = input_tag.get("value", "").strip()
                if color_name:
                    colors.append(color_name)
        return colors

    async def extract_colors_sizes(self) -> dict:
        color_size_map = {}

        color_blocks = self.soup.select('.variant-picker__option label.color-swatch span')
        if color_blocks:
            for block in color_blocks:
                color = block.get_text(strip=True)
                if color:
                    color_size_map[color] = []

            size_blocks = self.soup.select('.variant-picker__option label.block-swatch span')
            raw_sizes = [size.get_text(strip=True) for size in size_blocks if size.get_text(strip=True)]
            clean_sizes = [self._map_size(size) for size in raw_sizes]

            for color in color_size_map:
                color_size_map[color] = clean_sizes

        if not color_size_map:
            colors = await self.extract_colors_from_html()
            if colors:
                color_size_map = {color: [] for color in colors}

        logging.info(f"📦 Карта кольорів/розмірів (з HTML fallback): {color_size_map}")
        return color_size_map

    async def extract_color_size_availability(self) -> dict:
        stock = {}
        for script in self.soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product" and "offers" in data:
                    for offer in data["offers"]:
                        name = offer.get("name", "")
                        available = "InStock" in offer.get("availability", "")
                        if " / " in name:
                            color, size = name.split(" / ")
                            stock.setdefault(color.strip(), {})[self._map_size(size.strip())] = available
            except Exception as e:
                logging.warning(f"⚠️ JSON-LD parsing error: {e}")
        return stock

    async def determine_weight(self, title: str, description: str, image_url: str) -> float:
        weight_data = self.config.load_weight_data()
        weight = next((w for k, w in weight_data.items() if k in title.lower()), None)

        if weight is None:
            logging.info(f"🤖 Визначаємо вагу через GPT для: {title}")
            weight = self.translator.get_weight_estimate(title, description, image_url)
            self.config.update_weight_dict(title.lower(), weight)

        logging.info(f"✅ Визначена вага: {weight} кг")
        return weight

    async def is_product_available(self) -> bool:
        for script in self.soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product" and "offers" in data:
                    for offer in data["offers"]:
                        if "InStock" in offer.get("availability", ""):
                            return True
            except Exception as e:
                logging.warning(f"⚠️ JSON-LD parsing error: {e}")
        return False

    def _map_size(self, raw_size: str) -> str:
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        clean = re.sub(r'[^a-zA-Z]', '', raw_size)
        return size_mapping.get(clean, clean)

    # --- Форматування даних ---

    async def format_colors_with_stock(self) -> str:
        color_size_map = await self.extract_colors_sizes()
        stock_data = await self.extract_color_size_availability()

        if not stock_data:
            stock_data = {
                color: {size: True for size in sizes}
                for color, sizes in color_size_map.items()
            }

        return ColorSizeFormatter.format_color_size_availability(stock_data)

    async def parse(self) -> Dict[str, Any]:
        if not await self.fetch_page():
            return {}

        title = await self.extract_title()
        description = await self.extract_description()
        image_url = await self.extract_image()
        colors_text = await self.format_colors_with_stock()
        weight = await self.determine_weight(title, description, image_url)
        images = await self.extract_all_images()
        price = await self.extract_price()
        currency = self.currency

        return {
            "title": title,
            "price": price,
            "currency": currency,
            "description": description,
            "main_image": image_url,
            "colors_sizes": colors_text,
            "images": images,
            "weight": weight
        }

    async def get_product_info(self) -> tuple:
        try:
            data = await self.parse()
            self.page_source = getattr(self, "page_source", None)

            title = str(data.get("title", "Нет названия"))
            description = str(data.get("description", "Нет описания"))
            image_url = str(data.get("main_image", ""))
            colors_sizes = str(data.get("colors_sizes", ""))
            currency = str(data.get("currency", "USD"))
            images = data.get("images", [])

            price = float(data.get("price", 0.0))
            weight = float(data.get("weight", 0.5))

            logging.info(
                f"📦 Отримано товар: {title}, ціна: {price}, вага: {weight}, валюта: {currency}"
            )

            return title, price, description, image_url, weight, colors_sizes, images, currency

        except Exception as e:
            logging.exception(f"❌ Помилка при парсингу товару: {e}")
            return "Помилка", 0.0, "Помилка", "", 0.5, "", [], "USD"

    @property
    def currency(self) -> str:
        return self._currency
