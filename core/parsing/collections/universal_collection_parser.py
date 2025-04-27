""" 🧾 universal_collection_parser.py — Універсальний парсер колекцій YoungLA (US, EU, UK).

🔹 Функціонал:
- Визначає регіон сайту за URL
- Завантажує HTML-сторінку з WebDriverService
- Першочергово парсить JSON-LD
- Має fallback на DOM-парсинг
- Видає список товарів (href)

✅ SOLID:
- SRP: відповідає тільки за парсинг колекцій
- OCP: розширюється без змін структури (можна додати інші формати)
"""

import json
import logging
import asyncio
from bs4 import BeautifulSoup
from core.webdriver.webdriver_service import WebDriverService


class UniversalCollectionParser:
    """ 🧾 Парсер сторінок колекцій YoungLA з підтримкою регіонів US 🇺🇸, EU 🇪🇺, UK 🇬🇧.

    Основні функції:
    - Визначає валюту
    - Завантажує HTML-сторінку
    - Першочергово пробує парсити JSON-LD
    - Має fallback на DOM
    """

    def __init__(self, url: str):
        self.url = url
        self.soup = None
        self.page_source = None
        self.currency = self._detect_currency()

    def _detect_currency(self) -> str:
        """ 🌍 Визначає валюту/регіон за URL.
        """
        if "eu." in self.url:
            return "EUR"
        elif "uk." in self.url:
            return "GBP"
        return "USD"

    async def fetch_page(self) -> bool:
        """
        🌐 Завантажує HTML сторінку колекції через WebDriver.
        """
        self.page_source = await asyncio.to_thread(WebDriverService().fetch_page_source, self.url)

        if self.page_source and len(self.page_source) > 1000:
            self.soup = BeautifulSoup(self.page_source, "html.parser")
            logging.info(f"✅ Сторінка колекції завантажена: {self.url}")
            return True

        logging.error(f"❌ Не вдалося завантажити сторінку: {self.url}")
        return False

    async def extract_product_links(self) -> list[str]:
        """ 🔗 Витягує всі посилання на товари:
        - Через JSON-LD
        - Через DOM (fallback)

        :return: Список URL-адрес
        """
        if not await self.fetch_page():
            logging.warning("❌ Сторінка не завантажена — повертаємо порожній список.")
            return []

        product_links = []

        # 🔍 Парсимо JSON-LD
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string.strip())
                if data.get("@type") == "CollectionPage" and "mainEntity" in data:
                    for item in data["mainEntity"].get("itemListElement", []):
                        url = item.get("item", {}).get("url")
                        if url:
                            product_links.append(url)

                if product_links:
                    logging.info(f"✅ Знайдено {len(product_links)} товарів через JSON-LD")
                    return product_links

            except Exception as e:
                logging.warning(f"⚠️ JSON-LD парсинг: {e}")

        # 🔁 Якщо не знайдено — парсимо DOM
        logging.info("🔁 JSON-LD порожній, пробуємо парсити DOM...")

        try:
            product_elements = self.soup.select("a[href*='/products/']")
            for a in product_elements:
                href = a.get("href")
                if href and "/products/" in href:
                    full_url = self._build_full_url(href)
                    if full_url not in product_links:
                        product_links.append(full_url)

            if product_links:
                logging.info(f"📦 Знайдено {len(product_links)} товарів через DOM.")
            else:
                logging.warning("⚠️ DOM-парсинг не дав жодного результату. Можливо, змінилась структура сайту?")

        except Exception as e:
            logging.error(f"❌ Помилка парсингу DOM: {e}")

        return product_links

    def _build_full_url(self, href: str) -> str:
        """ 🏗️ Формує повний URL товару на основі відносного посилання.
        """
        base = "https://eu.youngla.com" if "eu." in self.url else \
               "https://uk.youngla.com" if "uk." in self.url else \
               "https://www.youngla.com"
        return href if href.startswith("http") else f"{base}{href}"

    def _get_domain(self) -> str:
        """ 🌐 Повертає домен сайту (без https://).
        """
        if "eu." in self.url:
            return "eu.youngla.com"
        elif "uk." in self.url:
            return "uk.youngla.com"
        return "www.youngla.com"

    def get_currency(self) -> str:
        """ 💱 Повертає валюту сайту.
        """
        return self.currency