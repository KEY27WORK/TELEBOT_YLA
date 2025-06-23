# base_parser.py
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
from core.parsers.unified_parser import UnifiedParser   # Updated import
from utils.region_utils import get_currency_from_url
# (ColorSizeFormatter will be used via UnifiedParser.format_availability)
from models.product_info import ProductInfo

# 🖥 Вивід у консоль
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TextColumn

class BaseParser:
    """
    📦 Основний асинхронний парсер товарів YoungLA.

    Відповідає за:
    - Завантаження сторінки через Playwright
    - Витяг даних (назва, опис, ціна, розміри, фото)
    - Парсинг наявності розмірів (JSON-LD або HTML)
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
        """Асинхронно завантажує сторінку товару. Повертає True, якщо успішно."""
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
                                # Парсимо HTML, якщо сторінку отримано
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

    # --- Основні методи витягування даних --- (title, price, description, images, etc.)

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
        """🔁 (Депрековано) Фолбек-метод: витягує список кольорів з HTML, якщо JSON-LD дані відсутні."""
        colors = []
        swatch_block = self.soup.find("div", class_="product-form__swatch color")
        if swatch_block:
            for input_tag in swatch_block.find_all("input", {"name": "Color"}):
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
        🔍 Швидка перевірка: чи є товар в наявності (на основі JSON-LD).
        Повертає True, якщо знайдено хоча б одну позицію InStock.
        """
        for script in self.soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict) and data.get("@type") == "Product" and "offers" in data:
                    for offer in data["offers"]:
                        if "InStock" in offer.get("availability", ""):
                            return True
            except Exception as e:
                logging.warning(f"⚠️ JSON-LD parsing error: {e}")
        return False

    async def get_stock_data(self) -> Dict[str, Dict[str, bool]]:
        """
        🗃️ Витягує повну карту наявності товару: {color: {size: bool}}.
        Забезпечує завантаження сторінки та застосовує об'єднаний парсинг наявності.
        """
        if not self.page_source:
            if not await self.fetch_page():
                return {}
        # Отримуємо дані про наявність через єдиний парсер (спершу JSON-LD, далі Legacy при необхідності)
        stock_data = UnifiedParser.parse_availability(self.page_source)
        return stock_data

    async def format_colors_with_stock(self) -> str:
        """
        Форматує карту кольорів та розмірів для Telegram.
        """
        stock_data = await self.get_stock_data()
        return UnifiedParser.format_availability(stock_data)

    async def parse(self) -> Dict[str, Any]:
        """
        📥 Парсить сторінку та збирає всі доступні дані про товар.
        Повертає словник із ключовою інформацією.
        """
        if not await self.fetch_page():
            return {}
        # Паралельно отримуємо основні поля товару
        title_task = self.extract_title()
        description_task = self.extract_description()
        sections_task = self.extract_detailed_sections()
        image_task = self.extract_image()
        colors_task = self.format_colors_with_stock()   # availability info (formatted text)
        images_task = self.extract_all_images()
        price_task = self.extract_price()
        title, description, detailed_sections, image_url, colors_text, images, price = await asyncio.gather(
            title_task, description_task, sections_task, image_task, colors_task, images_task, price_task
        )
        # Якщо опис надто короткий, доповнюємо першим розділом з detail-розділів
        if not description or len(description.strip()) < 20:
            if detailed_sections:
                first_key = next(iter(detailed_sections))
                description = detailed_sections[first_key]
        weight = await self.determine_weight(title, description, image_url)
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
        🔄 Обгортає результат парсингу у dataclass ProductInfo.
        Повертає об'єкт ProductInfo або заповнює поля "Помилка" у разі невдачі.
        """
        try:
            data = await self.parse()
            # Зберігаємо page_source для можливого повторного використання
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
