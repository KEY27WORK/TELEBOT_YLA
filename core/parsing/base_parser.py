"""
base_parser.py — Абстрактний базовий клас для парсингу сторінок товарів.

Цей модуль:
- Визначає базові методи для отримання даних з вебсторінок.
- Використовує Selenium для завантаження HTML-коду та BeautifulSoup для парсингу.
- Містить асинхронні методи для завантаження сторінки та визначення ваги.

Залежності:
- abc (для створення абстрактних класів)
- re (регулярні вирази)
- logging (логування інформації)
- BeautifulSoup (парсинг HTML)
- WebDriverService (сервіс Selenium WebDriver)
- TranslatorService, ConfigService (вага та GPT)
"""

import re
import logging
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from core.webdriver.webdriver_service import WebDriverService
from core.config.config_service import ConfigService
from bot.content.translator import TranslatorService
from typing import Dict, Any
import asyncio
import time

class BaseParser(ABC):
    """Абстрактний базовий клас парсера для сторінок товарів."""

    def __init__(self, url, currency_service):
        """
        Ініціалізація базового парсера.

        :param url: URL-адреса сторінки товару.
        :param currency_service: сервіс для роботи з валютами.
        """
        self.url = url
        self.currency_service = currency_service
        self.page_source = None
        self.soup = None
        self.config = ConfigService()
        self.translator = TranslatorService()

    async def fetch_page(self, retries: int = 5) -> bool:
        """
        Асинхронно завантажує HTML-сторінку з повторними спробами.

        :param retries: Кількість спроб.
        :return: Чи вдалося завантажити сторінку.
        """
        self.page_source = None  # <-- Явно обнуляем перед загрузкой

        start_time = time.time()  # Начало отсчёта времени
        for attempt in range(1, retries + 1):
            self.page_source = await asyncio.to_thread(WebDriverService().fetch_page_source, self.url)
            if self.page_source:
                self.soup = BeautifulSoup(self.page_source, "html.parser")
                logging.info(f"✅ Завантажено сторінку: {self.url}")

                elapsed_time = time.time() - start_time
                logging.info(f"⏳ Время загрузки страницы: {elapsed_time:.2f} сек.")
                return True
            logging.warning(f"🔄 Спроба {attempt}: не вдалося... {self.url}")
            time.sleep(3)  # Задержка перед следующей попыткой


        logging.error(f"❌ Не вдалося завантажити сторінку: {self.url}")
        return False
    
    async def extract_title(self) -> str:
        title_tag = self.soup.find("h1")
        return title_tag.text.strip() if title_tag else "Без назви"

    async def extract_price(self) -> float:
        price_meta = self.soup.find("meta", {"property": "product:price:amount"})
        if price_meta:
            try:
                raw_price = price_meta["content"].replace(",", ".")
                return float(raw_price)
            except ValueError as e:
                logging.warning(f"⚠️ Не удалось распарсить цену: {price_meta['content']}")
        return 0.0


    async def extract_description(self) -> str:
        desc_meta = self.soup.find("meta", {"name": "twitter:description"})
        return desc_meta["content"] if desc_meta else "Опис відсутній"

    async def extract_image(self) -> str:
        img_meta = self.soup.find("meta", {"property": "og:image"})
        return img_meta["content"] if img_meta else "Зображення відсутнє"

    async def extract_all_images(self) -> list[str]:
        images = []
        logging.info("🔍 Поиск изображений на странице...")
        gallery = self.soup.select_one(".product-gallery__thumbnail-list")
        if gallery:
            logging.info("✅ Галерея изображений найдена!")
            for img in gallery.select("button img[src]"):
                url = img["src"]
                if url.startswith("//"):
                    url = "https:" + url
                images.append(url)
                logging.info(f"📸 Найдено изображение: {url}")
            logging.info(f"📊 Всего найдено изображений: {len(images)}")
        return images

    async def format_colors_sizes(self, colors_sizes: dict) -> str:
        """
        Преобразует словарь цветов и размеров в читаемый формат для Telegram.

        :param colors_sizes: Словарь {"Black": ["XS", "S", "M"], "Blue": ["S", "M", "L"]}
        :return: Строка с форматированным списком.
        """
        if not colors_sizes:
            return "❌ Дані про кольори та розміри відсутні."

        formatted_sizes = "\n".join([f"• {color}: {', '.join(sizes)}" for color, sizes in colors_sizes.items()])
        return f"{formatted_sizes}"

    async def extract_colors_sizes(self) -> dict:
        """
        Извлекает доступные цвета и размеры товара.

        :return: Словарь с цветами и размерами: { "Цвет": ["Размер1", "Размер2", ...] }
        """
        color_size_map = {}

        # 🔹 Извлекаем цвета (из классов типа `.color-swatch span`)
        color_blocks = self.soup.select('.variant-picker__option label.color-swatch span')
        for block in color_blocks:
            color_name = block.get_text(strip=True)
            if color_name:
                color_size_map[color_name] = []

        # 🔹 Извлекаем размеры (из `.block-swatch span`)
        size_blocks = self.soup.select('.variant-picker__option label.block-swatch span')

        # 🔹 Маппинг нестандартных названий размеров
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }

        # 🔹 Обрабатываем список размеров, удаляя лишние символы
        raw_sizes = [size.get_text(strip=True) for size in size_blocks if size.get_text(strip=True)]
        clean_sizes = [size_mapping.get(re.sub(r'[^a-zA-Z]', '', size), size) for size in raw_sizes]

        # 🔹 Заполняем карту размеров для каждого цвета
        for color in color_size_map:
            color_size_map[color] = clean_sizes

        logging.info(f"🔍 Заполненая карта размеров для каждого цвета: {color_size_map}")
        return await self.format_colors_sizes(color_size_map)
    

    async def determine_weight(self, title: str, description: str, image_url: str) -> float:
        """
        Определяет вес товара, используя локальную базу или GPT.

        :param title: Название товара.
        :param description: Описание товара.
        :param image_url: Ссылка на изображение.
        :return: Вес товара в кг.
        """
        weight_data = self.config.load_weight_data()
        weight = next((w for k, w in weight_data.items() if k in title.lower()), None)

        if weight is None:  # Если нет в базе, запрашиваем у GPT
            logging.info(f"🔍 Определяем вес товара через GPT: {title}")
            weight = self.translator.get_weight_estimate(title, description, image_url)
            self.config.update_weight_dict(title.lower(), weight)  # Обновляем базу

        logging.info(f"✅ Определенный вес товара: {weight} кг")
        return weight

    @abstractmethod
    async def parse(self) -> Dict[str, Any]:
        """Асинхронний метод, який має бути реалізований у кожному конкретному парсері."""
        pass

