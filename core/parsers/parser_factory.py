"""
🏭 parser_factory.py — Фабрика для вибору відповідного парсера товару або колекції за URL.

📦 Повертає:
- BaseParser — для парсингу товарів
- UniversalCollectionParser — для парсингу колекцій
"""

# 🧱 Парсери
from core.parsers.base_parser import BaseParser
from core.parsers.collections.universal_collection_parser import UniversalCollectionParser


class ParserFactory:
    @staticmethod
    def get_product_parser(url: str) -> BaseParser:
        """🔎 Повертає парсер товару (BaseParser)"""
        return BaseParser(url)

    @staticmethod
    def get_collection_parser(url: str) -> UniversalCollectionParser:
        """🔎 Повертає парсер колекції (UniversalCollectionParser)"""
        return UniversalCollectionParser(url)
