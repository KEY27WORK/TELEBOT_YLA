# 📦 app/infrastructure/parsers/html_data_extractor.py
"""
📦 html_data_extractor.py — Низькорівневий екстрактор даних з HTML.

🔹 Використовує централізовані селектори для легкого оновлення.
🔹 Застосовує DRY-принцип через допоміжні методи.
🔹 Не містить бізнес-логіки, лише витягує "сирі" дані.
"""

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup, Tag										        # 🧽 BeautifulSoup для парсингу HTML, Tag — для типізації тегів (використовується для анотацій або розширення)

# 🔠 Системні імпорти
import json																		# 📦 JSON-десеріалізація для скриптів
import logging																	# 🧾 Логування подій
from typing import Dict, List, Optional, Union									# 🧰 Типи даних для анотацій
from dataclasses import dataclass												# 🧱 Зручна структура для селекторів


# ================================
# 🏛️ ГОЛОВНИЙ КЛАС ПАРСЕРА
# ================================
class HtmlDataExtractor:
    """
    🛠️ Витягує структуровану інформацію з HTML-документа товару.
    Працює з готовим об'єктом BeautifulSoup.
    """

    @dataclass(frozen=True)
    class Selectors:
        TITLE = "h1"																	                            # 🏷️ Заголовок товару
        PRICE = 'meta[property="product:price:amount"]'								                                # 💰 Ціна
        DESCRIPTION = 'meta[name="twitter:description"]'								                            # 📝 Короткий опис
        MAIN_IMAGE = 'meta[property="og:image"]'										                            # 🖼️ Головне зображення
        ALL_IMAGES = ".product-gallery__thumbnail img[src], .product-gallery__thumbnail-list img[src]"	            # 🖼️ Усі превʼю
        DETAILED_SECTIONS = "#ProductAccordion details"								                                # 📄 Детальні секції (опис, fit, care)
        JSON_LD_SCRIPT = 'script[type="application/ld+json"]'						                                # 📦 JSON-LD для наявності
        LEGACY_STOCK_SCRIPT = "script#ProductJson"									                                # 📦 Legacy JSON про наявність

    def __init__(self, soup: BeautifulSoup):
        self.soup = soup																                            # 🥣 Об'єкт BeautifulSoup

    # ================================
    # 🧩 ПУБЛІЧНІ МЕТОДИ ВИТЯГАННЯ
    # ================================

    def extract_title(self) -> str:
        """🏷️ Витягує заголовок H1."""
        return self._find_and_get_text(self.Selectors.TITLE, default="Без назви")

    def extract_price(self) -> float:
        """💰 Витягує ціну з мета-тегу."""
        price_str = self._find_and_get_attribute(self.Selectors.PRICE, "content")				       # 🔎 Отримуємо атрибут content
        try:
            return float(price_str.replace(",", ".")) if price_str else 0.0					           # ✅ Приводимо до float
        except (ValueError, TypeError):
            logging.warning(f"⚠️ Неможливо розпізнати ціну: {price_str}")				                # 🚨 Невалідна ціна
            return 0.0

    def extract_description(self) -> str:
        """📝 Витягує опис з мета-тегу."""
        return self._find_and_get_attribute(self.Selectors.DESCRIPTION, "content")			           # 📥 Повертає атрибут content

    def extract_main_image(self) -> str:
        """🖼️ Витягує головне зображення."""
        return self._find_and_get_attribute(self.Selectors.MAIN_IMAGE, "content")				       # 📥 URL зображення

    def extract_all_images(self) -> List[str]:
        """🖼️ Витягує всі унікальні зображення товару."""
        unique_urls = set()																	           # 🔁 Множина для унікальних URL
        for img_tag in self.soup.select(self.Selectors.ALL_IMAGES):							           # 🔎 Всі теги img
            if src := img_tag.get("src"):														       # 🧲 Якщо є src
                full_url = self._normalize_image_url(src)										       # 🔗 Нормалізуємо
                unique_urls.add(full_url)														       # ➕ Додаємо до множини
        logging.info(f"📸 Знайдено {len(unique_urls)} унікальних зображень.")					       # 🧾 Лог про кількість
        return list(unique_urls)

    def extract_detailed_sections(self) -> Dict[str, str]:
        """📄 Витягує секції 'Description', 'Fit', 'Materials & Care'."""
        sections = {}																			       # 📁 Порожній словник
        for detail in self.soup.select(self.Selectors.DETAILED_SECTIONS):						       # 🔍 Шукаємо всі details
            summary = detail.find("summary")													       # 🧾 Назва секції
            body = detail.find("div")															       # 📄 Контент секції
            if summary and body:
                title = summary.get_text(strip=True).upper()									       # 🔠 Назва секції
                content = body.get_text(separator="\n", strip=True)							           # 📦 Вміст
                sections[title] = content														       # ➕ Додаємо до словника
        return sections

    def extract_stock_from_json_ld(self) -> Optional[Dict[str, Dict[str, bool]]]:
        """📦 Парсить дані про наявність з JSON-LD."""
        for script in self.soup.select(self.Selectors.JSON_LD_SCRIPT):							       # 🔍 Ітеруємо всі скрипти
            try:
                if script.string:																       # 🧠 Якщо є JSON-рядок
                    data = json.loads(script.string)											       # 📥 Завантажуємо JSON
                    if data.get("@type") == "Product" and "offers" in data:					           # ✅ Перевіряємо тип
                        return self._parse_json_ld_offers(data["offers"])						       # 🧩 Розбираємо
            except (json.JSONDecodeError, AttributeError):										       # ❌ Некоректний JSON
                continue
        return None																			           # 🔚 Не знайдено

    def extract_stock_from_legacy(self) -> Optional[Dict[str, Dict[str, bool]]]:
        """📦 Парсить дані про наявність із вбудованого JSON (ProductJson)."""
        script_tag = self.soup.select_one(self.Selectors.LEGACY_STOCK_SCRIPT)					       # 🔍 Шукаємо скрипт
        if script_tag and script_tag.string:
            try:
                product_data = json.loads(script_tag.string)									       # 📥 Завантажуємо JSON
                return self._parse_legacy_variants(product_data.get("variants", []))			       # 🧩 Розбираємо варіанти
            except json.JSONDecodeError as e:
                logging.warning(f"⚠️ Помилка JSON-десеріалізації ProductJson: {e}")			            # 🚨 Помилка розбору
        return None																			           # 🔚 Не знайдено

    # ================================
    # 🕵️‍♂️ ПРИВАТНІ ДОПОМІЖНІ МЕТОДИ
    # ================================

    def _find_and_get_text(self, selector: str, default: str = "") -> str:
        """Знаходить тег за селектором і повертає його текст."""
        tag = self.soup.select_one(selector)													        # 🔍 Один тег
        return tag.get_text(strip=True) if tag else default									            # 📤 Текст або дефолт

    def _find_and_get_attribute(self, selector: str, attr: str, default: str = "") -> str:
        """Знаходить тег і повертає значення його атрибута."""
        tag = self.soup.select_one(selector)													        # 🔍 Один тег
        return tag.get(attr, default) if tag and tag.has_attr(attr) else default				        # 📤 Атрибут або дефолт

    def _normalize_image_url(self, src: str) -> str:
        """
        🔗 Приводить URL зображення до повного формату (додає 'https:').
        """
        return f"https:{src}" if src.startswith("//") else src									        # 🧹 Додаємо https: якщо треба

    def _parse_json_ld_offers(self, offers: Union[Dict, List[Dict]]) -> Dict:
        """
        Парсить секцію 'offers' з JSON-LD, яка може бути об'єктом або списком.
        """
        offers_list = [offers] if isinstance(offers, dict) else offers							        # 🔁 Один або список

        stock = {}																				        # 📦 Ініціалізація
        for offer in offers_list:
            name = offer.get("name", "")														        # 🏷️ Назва (color / size)
            available = "InStock" in offer.get("availability", "")								        # ✅ Статус наявності
            if " / " in name:
                color, size = name.split(" / ", 1)												        # 🎨 / 📏
                stock.setdefault(color.strip(), {})[size.strip()] = available					        # ➕ Додаємо до словника
        return stock

    def _parse_legacy_variants(self, variants: List[Dict]) -> Dict:
        """Парсить секцію 'variants' з legacy JSON."""
        stock = {}																				                    # 📦 Ініціалізація
        for var in variants:
            color, size = var.get("option1"), var.get("option2")								                    # 🎨 / 📏 Витягуємо параметри
            if color and size:
                stock.setdefault(str(color).strip(), {})[str(size).strip()] = var.get("available", False)	        # ➕ Додаємо
        return stock