""" 🧠 base_parser.py — Абстрактний базовий клас для парсингу сторінок товарів YoungLA.

🔹 Клас `BaseParser`:
- Визначає базові асинхронні методи для парсингу сторінок
- Завантажує HTML через Selenium WebDriver
- Використовує BeautifulSoup для обробки DOM
- Витягує ціну, опис, зображення, розміри, вагу

Залежності:
- abc, re, logging, asyncio, json, time
- BeautifulSoup
- WebDriverService (Selenium)
- ConfigService (вага)
- TranslatorService (визначення ваги через GPT)
"""

# 📦 Стандартні
import re
import time
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any

# 🌐 Парсинг HTML
from bs4 import BeautifulSoup

# 🧱 Сервіси
from core.webdriver.webdriver_service import WebDriverService
from core.config.config_service import ConfigService
from bot.content.translator import TranslatorService


class BaseParser(ABC):
    """🧠 Абстрактний базовий клас для всіх товарних парсерів YoungLA."""

    def __init__(self, url: str, currency_service: Any):
        """
        :param url: Посилання на сторінку товару
        :param currency_service: (не використовується, залишено для сумісності)
        """
        self.url = url
        self.currency_service = currency_service
        self.page_source = None
        self.soup = None
        self.config = ConfigService()
        self.translator = TranslatorService()

    async def fetch_page(self, retries: int = 5) -> bool:
        """🌐 Завантажує HTML-код сторінки через WebDriverService."""
        self.page_source = None
        start_time = time.time()

        for attempt in range(1, retries + 1):
            self.page_source = await WebDriverService().fetch_page_source(self.url)

            if self.page_source:
                self.soup = BeautifulSoup(self.page_source, "html.parser")
                logging.info(f"✅ Сторінку завантажено: {self.url}")
                logging.info(f"⏳ Час завантаження: {time.time() - start_time:.2f} сек.")
                return True
            
            title_tag = self.soup.find("h1")
            page_not_found = "Page Not Found" in self.page_source or "Your connection needs to be verified" in self.page_source
            
            if not title_tag or page_not_found:
                logging.warning(f"⚠️ Підозріла сторінка (немає h1 або Cloudflare-заглушка): спроба {attempt}")
                await asyncio.sleep(2)
                continue

            logging.warning(f"🔄 Спроба {attempt}: не вдалося завантажити сторінку...")
            await asyncio.sleep(2)

        logging.error(f"❌ Не вдалося завантажити сторінку: {self.url}")
        return False

    def _map_size(self, raw_size: str) -> str:
        """🎯 Приводить розміри до скорочених позначень (наприклад, Medium → M)."""
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        clean = re.sub(r'[^a-zA-Z]', '', raw_size)
        return size_mapping.get(clean, clean)

    async def extract_title(self) -> str:
        """📝 Витягує заголовок товару (h1)."""
        title_tag = self.soup.find("h1")
        return title_tag.text.strip() if title_tag else "Без назви"

    async def extract_price(self) -> float:
        """💲 Витягує ціну з мета-тегу."""
        meta = self.soup.find("meta", {"property": "product:price:amount"})
        if meta:
            try:
                return float(meta["content"].replace(",", "."))
            except ValueError:
                logging.warning(f"⚠️ Неможливо розпізнати ціну: {meta['content']}")
        return 0.0

    async def extract_description(self) -> str:
        """🧾 Витягує короткий опис товару з Twitter мета-тегу."""
        meta = self.soup.find("meta", {"name": "twitter:description"})
        return meta["content"] if meta else "Опис відсутній"

    async def extract_image(self) -> str:
        """🖼️ Витягує головне зображення з og:image."""
        meta = self.soup.find("meta", {"property": "og:image"})
        return meta["content"] if meta else "Зображення відсутнє"

    async def extract_all_images(self) -> list[str]:
        """🖼️ Витягує всі зображення з галереї товару."""
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

    async def format_colors_sizes(self, colors_sizes: dict) -> str:
        """🎨 Форматує словник {колір: [розміри]} у список для Telegram."""
        if not colors_sizes:
            return "❌ Дані про кольори та розміри відсутні."

        lines = []
        for color, sizes in colors_sizes.items():
            if sizes:
                line = f"• {color}: {', '.join(sizes)}"
            else:
                line = f"• {color}"
            lines.append(line)

        return "\n".join(lines)


    async def extract_colors_from_html(self) -> list[str]:
        """
        🎨 Витягує список кольорів з HTML (не через JSON-LD).
    
        :return: Список назв кольорів
        """
        colors = []
        swatch_block = self.soup.find("div", class_="product-form__swatch color")
        if not swatch_block:
            return colors
    
        inputs = swatch_block.find_all("input", {"name": "Color"})
        for input_tag in inputs:
            color_name = input_tag.get("value", "").strip()
            if color_name:
                colors.append(color_name)
    
        return colors
    
    async def extract_colors_sizes(self) -> dict:
        """
        🎯 Витягує карту кольорів і розмірів без перевірки наявності.
        Якщо немає повних даних — підтягує кольори з HTML.
    
        :return: Словник {колір: [розміри]} або просто {колір: []}
        """
        color_size_map = {}
    
        # 🧠 1. Спроба витягти кольори/розміри через стандартний варіант
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
    
        # 🛠 2. Якщо кольорів через стандартний шлях немає — пробуємо через HTML
        if not color_size_map:
            colors = await self.extract_colors_from_html()
            if colors:
                color_size_map = {color: [] for color in colors}
    
        logging.info(f"📦 Карта кольорів/розмірів (з HTML fallback): {color_size_map}")
        return color_size_map
    

    async def extract_color_size_availability(self) -> dict:
        """📊 Витягує дані про наявність кожного розміру в кожному кольорі з JSON-LD."""
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
                            color = color.strip()
                            size = self._map_size(size.strip())
                            stock.setdefault(color, {})[size] = available
            except Exception as e:
                logging.warning(f"⚠️ JSON-LD parsing error: {e}")
        return stock

    async def determine_weight(self, title: str, description: str, image_url: str) -> float:
        """⚖️ Визначає вагу товару: спочатку з config, інакше — через GPT."""
        weight_data = self.config.load_weight_data()
        weight = next((w for k, w in weight_data.items() if k in title.lower()), None)

        if weight is None:
            logging.info(f"🤖 Визначаємо вагу через GPT для: {title}")
            weight = self.translator.get_weight_estimate(title, description, image_url)
            self.config.update_weight_dict(title.lower(), weight)

        logging.info(f"✅ Визначена вага: {weight} кг")
        return weight

    @abstractmethod
    async def parse(self) -> Dict[str, Any]:
        """🔧 Метод, який має реалізувати дочірній парсер."""
        pass
