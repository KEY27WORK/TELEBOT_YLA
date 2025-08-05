# 🧠 app/infrastructure/parsers/__init__.py
"""
🧠 Модуль `parsers` — логіка парсингу сторінок сайту YoungLA.

📌 Містить:
– Оркестратор повного парсингу товару (`BaseParser`)
– Екстрактор даних із DOM (`HtmlDataExtractor`)
– Фабрику для створення парсерів (`ParserFactory`)
– Парсери колекцій та пошуку (`UniversalCollectionParser`, `ProductSearchResolver`)

⚙️ Інкапсулює складність витягування даних зі сторінок.
"""

# 🏗️ Основні класи
from .base_parser import BaseParser
from .html_data_extractor import HtmlDataExtractor
from .parser_factory import ParserFactory

# 📚 Парсери колекцій
from .collections.universal_collection_parser import UniversalCollectionParser

# 🔎 Пошук (✅ правильний клас)
from .product_search.search_resolver import ProductSearchResolver

__all__ = [
    "BaseParser",
    "HtmlDataExtractor",
    "ParserFactory",
    "UniversalCollectionParser",
    "ProductSearchResolver",
]
