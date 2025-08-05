# 🧾 app/infrastructure/parsers/collections/universal_collection_parser.py
"""
🧾 universal_collection_parser.py — Універсальний парсер колекцій YoungLA.

🔹 Клас `UniversalCollectionParser`:
- Визначає регіон сайту за URL.
- Завантажує HTML-сторінку через WebDriverService.
- Парсить посилання на товари, віддаючи перевагу JSON-LD.
- Інкапсулює логіку побудови базових URL через UrlParserService.
"""

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup												        # 🧽 Парсинг HTML

# 🔠 Системні імпорти
import json															                # 📦 Робота з JSON
import logging														                # 🧾 Логування
from typing import List, Optional										            # 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService								    # ⚙️ Конфігурація
from app.domain.products.interfaces import ICollectionDataProvider					# 🧱 Контракт парсера
from app.infrastructure.web.webdriver_service import WebDriverService				# 🌍 Завантаження HTML
from app.shared.utils.url_parser_service import UrlParserService					# 🧠 Сервіс побудови URL


# ================================
# 🏛️ КЛАС ПАРСЕРА КОЛЕКЦІЙ
# ================================
class UniversalCollectionParser(ICollectionDataProvider):
    """
    🧾 Парсер колекцій товарів з сайтів YoungLA (US 🇺🇸, EU 🇪🇺, UK 🇬🇧).
    Використовується для витягування усіх посилань на товари в колекції.
    """

    MIN_PAGE_LENGTH_BYTES = 1000											        # 📏 Мінімальна довжина HTML для валідності

    def __init__(
        self,
        url: str,
        webdriver_service: WebDriverService,
        config_service: ConfigService,
        url_parser_service: UrlParserService
    ):
        """
        ⚙️ Ініціалізація парсера з впровадженими залежностями.
        """
        self.url = url													            # 🔗 URL колекції
        self.webdriver_service = webdriver_service								    # 🌍 Сервіс браузера
        self.config_service = config_service									    # ⚙️ Конфігурація для доменів
        self.url_parser_service = url_parser_service							    # 🧠 Сервіс для визначення валюти та домену

        self.soup: Optional[BeautifulSoup] = None								    # 🧽 Розпарсений DOM
        self.page_source: Optional[str] = None									    # 📄 Сирий HTML
        self.currency = self.url_parser_service.get_currency(self.url)				# 💱 Витягуємо регіон з URL

    # ================================
    # 🔗 ОСНОВНИЙ МЕТОД
    # ================================
    async def get_product_links(self) -> List[str]:
        """
        🔗 Витягує всі посилання на товари з колекції.
        """
        if not await self._fetch_page():
            logging.warning("❌ Сторінка не завантажена — повертаємо порожній список.")
            return []

        links = self._parse_from_json_ld()										# 📄 Спочатку пробуємо JSON-LD
        if links:
            logging.info(f"✅ Знайдено {len(links)} товарів через JSON-LD.")
            return links

        logging.info("🔁 JSON-LD не спрацював. Пробуємо парсити DOM...")
        links = self._parse_from_dom()											# 🌐 Фолбек — DOM-парсинг
        if links:
            logging.info(f"📦 Знайдено {len(links)} товарів через DOM.")
        else:
            logging.warning("⚠️ DOM-парсинг не дав жодного результату.")

        return links

    # ================================
    # 🕵️‍♂️ ПРИВАТНІ МЕТОДИ
    # ================================
    async def _fetch_page(self) -> bool:
        """
        🌐 Завантажує HTML-сторінку колекції через WebDriverService.
        """
        self.page_source = await self.webdriver_service.fetch_page_source(self.url)                         # 🌍 Отримуємо HTML через браузер

        if self.page_source and len(self.page_source) > self.MIN_PAGE_LENGTH_BYTES:                         # ✅ Перевірка: чи не порожня сторінка
            self.soup = BeautifulSoup(self.page_source, "html.parser")                                      # 🧽 Створюємо DOM-дерево
            logging.info(f"✅ Сторінка колекції завантажена: {self.url}")
            return True

        logging.error(f"❌ Не вдалося завантажити сторінку: {self.url}")                                    # 🧯 Лог помилки при фейлі
        return False

    def _parse_from_json_ld(self) -> List[str]:
        """
        📄 Витягує посилання зі структурованих даних JSON-LD.
        """
        if not self.soup:                                                                           # 🛡️ Перевірка: чи є DOM
            return []

        links = []
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                if not script.string:                                                              # ⛔ JSON-пустий — пропускаємо
                    continue
                data = json.loads(script.string)
                if data.get("@type") == "CollectionPage" and "mainEntity" in data:
                    for item in data["mainEntity"].get("itemListElement", []):
                        if url := item.get("item", {}).get("url"):
                            links.append(url)
            except (json.JSONDecodeError, AttributeError):                                         # 🧯 Ігноруємо некоректні блоки
                continue
        return links

    def _parse_from_dom(self) -> List[str]:
        """
        🌐 Альтернативний метод: парсить DOM, шукаючи <a href="/products/...">.
        """
        if not self.soup:                                                                          # 🛡️ DOM ще не готовий
            return []

        unique_links = set()                                                                       # 🔁 Унікальність через set
        try:
            product_elements = self.soup.select('a[href*="/products/"]')                           # 🔎 Шукаємо всі посилання
            for a_tag in product_elements:
                if href := a_tag.get("href"):
                    full_url = self._build_full_url(href)                                          # 🧱 Склеюємо повний URL
                    unique_links.add(full_url)
        except Exception as e:
            logging.error(f"❌ Помилка парсингу DOM: {e}")                                         # 🧯 Ловимо всі фейли

        return list(unique_links)

    def _build_full_url(self, href: str) -> str:
        """
        🧱 Формує повний URL товару, використовуючи UrlParserService.
        """
        if href.startswith("http"):
            return href                                                                            # 🔗 Якщо вже повний — повертаємо як є

        base_url = self.url_parser_service.get_base_url(self.currency)                             # ⚙️ Отримуємо домен через сервіс
        return f"{base_url}{href}"                                                                 # 🔧 Склеюємо повний URL
