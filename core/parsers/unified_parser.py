# unified_parser.py
import json
import logging
from bs4 import BeautifulSoup

from core.parsers.json_ld_parser import JsonLdAvailabilityParser
from core.product_availability.formatter import ColorSizeFormatter

class LegacyAvailabilityParser:
    """
    🏷️ Парсер для старих сторінок (без JSON-LD) з використанням HTML або inline JSON.
    Витягує доступні кольори та розміри, і їх наявність.
    """
    @staticmethod
    def extract_color_size_availability(page_source: str) -> dict:
        """
        🕰 Витягує наявність товару (колір/розмір) зі старого шаблону сторінки.
        Повертає словник {color: {size: bool}}, або {color: {}} якщо дані про розміри відсутні.
        """
        stock = {}
        try:
            soup = BeautifulSoup(page_source, "html.parser")
        except Exception as e:
            logging.error(f"❌ Legacy parser: помилка парсингу HTML через BeautifulSoup: {e}")
            return stock
        # Спроба 1: пошук скрипту з даними продукту (ProductJson)
        product_json_script = soup.find("script", {"id": "ProductJson"})
        product_data = None
        if product_json_script:
            try:
                product_data = json.loads(product_json_script.string or "{}")
            except Exception as e:
                logging.warning(f"⚠️ Legacy parser: помилка JSON-деcеріалізації ProductJson: {e}")
        if product_data:
            variants = product_data.get("variants", [])
            option_names = product_data.get("options", [])
            # Отримуємо список назв опцій (наприклад, ["Color", "Size"] або одна опція)
            opt_names = []
            for opt in option_names:
                name = opt.get("name", "") if isinstance(opt, dict) else str(opt)
                opt_names.append(name.lower())
            if not opt_names:
                # Якщо назви опцій не вказані, визначаємо за полями варіантів
                if variants and 'option2' in variants[0] and variants[0].get('option2'):
                    opt_names = ["option1", "option2"]
                else:
                    opt_names = ["option1"]
            # Парсинг варіантів товару залежно від кількості опцій
            if len(opt_names) == 1:
                # Випадок: тільки одна опція (або тільки розмір, або тільки колір)
                only_opt = opt_names[0]
                if "size" in only_opt:
                    # Лише розміри (продукт без кольорових варіацій)
                    color_key = "Без кольору"
                    stock[color_key] = {}
                    for var in variants:
                        size_val = var.get("option1")
                        available = var.get("available", False)
                        if size_val:
                            size_clean = JsonLdAvailabilityParser._map_size(str(size_val).strip())
                            stock[color_key][size_clean] = available
                else:
                    # Лише кольори (без розмірів)
                    for var in variants:
                        color_val = var.get("option1")
                        available = var.get("available", False)
                        if color_val:
                            color_name = str(color_val).strip()
                            stock[color_name] = {}  # без деталізації розмірів
                            # *Примітка:* якщо потрібно, можна зберігати `available` десь окремо
            else:
                # Дві або більше опцій (припускаємо: option1 = колір, option2 = розмір)
                for var in variants:
                    available = var.get("available", False)
                    color_val = var.get("option1")
                    size_val = var.get("option2")
                    if color_val and size_val:
                        color_name = str(color_val).strip()
                        size_clean = JsonLdAvailabilityParser._map_size(str(size_val).strip())
                        stock.setdefault(color_name, {})[size_clean] = available
        # Спроба 2: якщо JSON-даних немає, отримуємо список кольорів із HTML (фолбек)
        if not stock:
            color_inputs = soup.find_all("input", {"name": "Color"})
            if color_inputs:
                for input_tag in color_inputs:
                    color = input_tag.get("value", "").strip()
                    if color:
                        stock[color] = {}
            else:
                color_select = soup.find("select", {"name": "Color"})
                if color_select:
                    for opt in color_select.find_all("option"):
                        color = opt.text.strip()
                        if color:
                            stock[color] = {}
        return stock

class UnifiedParser:
    """
    🕹️ Фасад для парсингу наявності товару, який об'єднує різні підходи (JSON-LD, Legacy HTML).
    """
    @staticmethod
    def parse_availability(page_source: str) -> dict:
        """
        🎯 Витягає карту наявності товару {color: {size: bool}} з HTML-коду сторінки.
        Спочатку намагається отримати дані через JSON-LD, 
        якщо розмірів не знайдено – використовує LegacyAvailabilityParser.
        """
        stock_data = JsonLdAvailabilityParser.extract_color_size_availability(page_source)
        if stock_data:
            # Перевіряємо, чи всі словники розмірів порожні (тобто JSON-LD знайшов лише кольори)
            all_sizes_empty = all(len(sizes) == 0 for sizes in stock_data.values())
            if all_sizes_empty:
                legacy_data = LegacyAvailabilityParser.extract_color_size_availability(page_source)
                if legacy_data:
                    stock_data = legacy_data
        else:
            # Якщо взагалі не знайдено JSON-LD інформації, пробуємо legacy-парсер прямо
            stock_data = LegacyAvailabilityParser.extract_color_size_availability(page_source)
        return stock_data

    @staticmethod
    def format_availability(stock_data: dict) -> str:
        """
        🎨 Форматує словник наявності у зручний текст для Telegram:
        "Color: sizes..." (або 🚫 якщо розміру немає).
        """
        return ColorSizeFormatter.format_color_size_availability(stock_data)
