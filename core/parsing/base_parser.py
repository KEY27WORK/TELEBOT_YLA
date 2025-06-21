"""
🧠 base_parser.py — Базовий клас для парсингу сторінок товарів YoungLA.

🔹 Клас `BaseParser`:
- Самостійно визначає валюту по URL
- Асинхронно завантажує HTML через Playwright
- Витягує ціну, опис, зображення, кольори, розміри, наявність
- Формує форматований словник для Telegram
"""

# 📦 Стандартні
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

# 🧰 Утиліти
from utils.region_utils import get_currency_from_url
from core.parsing.json_ld_parser import JsonLdAvailabilityParser

# 📦 Моделі даних
from models.product_info import ProductInfo

# 🖥 Вивід у консоль
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TextColumn


class BaseParser:
    """
    📦 Основний асинхронний парсер товарів YoungLA.

    Відповідає за:
    - Завантаження сторінки через Playwright
    - Витяг даних (назва, опис, ціна, розміри, фото)
    - Парсинг JSON-LD скриптів для наявності розмірів
    - Автоматичне визначення валюти
    - Формування готової структури для Telegram
    """

    def __init__(self, url: str, enable_progress: bool = True):
        self.url = url
        self._currency = get_currency_from_url(url)
        self.enable_progress = enable_progress
        self.page_source: Optional[str] = None
        self.soup: Optional[BeautifulSoup] = None
        self.config = ConfigService()
        self.translator = TranslatorService()

    async def fetch_page(self, retries: int = 5) -> bool:
        self.page_source = None
        start_time = time.time()

        for attempt in range(1, retries + 1):
            if self.enable_progress:
                with Progress(
                    SpinnerColumn(),
                    BarColumn(bar_width=24),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(),
                    transient=True,
                ) as progress:
                    task = progress.add_task(f"🌍 Завантаження (спроба {attempt})...", total=100)

                    for step in range(100):
                        if step % 5 == 0:
                            self.page_source = await WebDriverService().fetch_page_source(self.url)
                            if self.page_source:
                                self.soup = BeautifulSoup(self.page_source, "html.parser")
                                logging.info(f"✅ Сторінку завантажено: {self.url}")
                                logging.info(f"⏳ Час завантаження: {time.time() - start_time:.2f} сек.")
                                return True
                        await asyncio.sleep(0.05)
                        progress.update(task, advance=1)
            else:
                self.page_source = await WebDriverService().fetch_page_source(self.url)
                if self.page_source:
                    self.soup = BeautifulSoup(self.page_source, "html.parser")
                    return True
                await asyncio.sleep(2)

            logging.warning(f"🔄 Спроба {attempt}: не вдалося завантажити сторінку...")

        logging.error(f"❌ Не вдалося завантажити сторінку: {self.url}")
        return False

    # --- Основні методи витягування даних ---

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

    async def extract_detailed_sections(self) -> dict:
        sections = {}
        accordion = self.soup.select_one("#ProductAccordion")
        if accordion:
            for detail in accordion.select("details"):
                summary = detail.find("summary")
                body = detail.find("div")
                if summary and body:
                    key = summary.get_text(strip=True).upper()
                    value = body.get_text(separator="\n", strip=True)
                    sections[key] = value
        return sections

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
        # Залишаємо для fallback, якщо немає JSON-LD даних
        colors = []
        swatch_block = self.soup.find("div", class_="product-form__swatch color")
        if swatch_block:
            inputs = swatch_block.find_all("input", {"name": "Color"})
            for input_tag in inputs:
                color_name = input_tag.get("value", "").strip()
                if color_name:
                    colors.append(color_name)
        return colors

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
        """
        Перевіряє базову наявність товару в JSON-LD.

        Ця функція слугує швидкою булевою перевіркою,
        яку використовує AvailabilityManager для простої перевірки.
        """
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

    async def format_colors_with_stock(self) -> str:
        """
        Форматує карту кольорів та розмірів для Telegram.

        Використовує JsonLdAvailabilityParser для основного парсингу,
        якщо даних немає — fallback через extract_colors_from_html.
        """
        stock_data = JsonLdAvailabilityParser.extract_color_size_availability(self.page_source)

        if not stock_data:
            colors = await self.extract_colors_from_html()
            stock_data = {color: {} for color in colors}

        return ColorSizeFormatter.format_color_size_availability(stock_data)

    async def parse(self) -> Dict[str, Any]:
        """
        Головна точка входу: парсинг повного товару.

        Викликає всі необхідні методи для отримання інформації
        та формує словник для подальшої обробки.
        """
        if not await self.fetch_page():
            return {}

        title = await self.extract_title()
        description = await self.extract_description()
        detailed_sections = await self.extract_detailed_sections()

        if not description or len(description.strip()) < 20:
            if detailed_sections:
                first_key = next(iter(detailed_sections))
                description = detailed_sections[first_key]

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
            "weight": weight,
            "sections": detailed_sections,
            "image_url": image_url,
        }

    async def get_product_info(self) -> ProductInfo:
        """
        Конвертація даних парсера до ProductInfo dataclass.
        """
        try:
            data = await self.parse()
            self.page_source = getattr(self, "page_source", None)

            return ProductInfo(
                title=str(data.get("title", "Нет названия")),
                price=float(data.get("price", 0.0)),
                description=str(data.get("description", "Нет описания")),
                image_url=str(data.get("main_image", "")),
                weight=float(data.get("weight", 0.5)),
                colors_text=str(data.get("colors_sizes", "")),
                images=data.get("images", []),
                currency=str(data.get("currency", "USD")),
                sections=data.get("sections", {})
            )

        except Exception as e:
            logging.exception(f"❌ Помилка при парсингу товару: {e}")
            return ProductInfo(
                title="Помилка",
                price=0.0,
                description="Помилка",
                image_url="",
                weight=0.5,
                colors_text="",
                images=[],
                currency="USD",
                sections={}
            )

    @property
    def currency(self) -> str:
        """Визначена валюта товару по URL."""
        return self._currency