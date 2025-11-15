# 🧠 app/infrastructure/parsers/__init__.py
"""
🧠 Пакет інфраструктурних парсерів для YoungLA.

🔹 `BaseParser` + `HtmlDataExtractor` — повний цикл парсингу товарної сторінки.
🔹 `ParserFactory` / `ParserFactoryAdapter` — фабрика та адаптер під доменні контракти.
🔹 `UniversalCollectionParser` — обробка колекцій.
🔹 `ProductSearchResolver` — парсинг результатів пошуку.
🔹 `ParserInfraOptions` — конфігурація інфраструктурних опцій.
"""

from __future__ import annotations

# 🏗️ Базові компоненти
from .base_parser import BaseParser
from .html_data_extractor import HtmlDataExtractor

# 🧩 Фабрика парсерів
from .factory_adapter import ParserFactoryAdapter
from .parser_factory import ParserFactory
from ._infra_options import ParserInfraOptions
from .contracts import IParserFactory

# 📚 Колекції
from .collections.universal_collection_parser import UniversalCollectionParser

# 🔎 Пошук
from .product_search.search_resolver import ProductSearchResolver

__all__ = [
    "BaseParser",
    "HtmlDataExtractor",
    "ParserFactory",
    "ParserFactoryAdapter",
    "ParserInfraOptions",
    "IParserFactory",
    "UniversalCollectionParser",
    "ProductSearchResolver",
]
