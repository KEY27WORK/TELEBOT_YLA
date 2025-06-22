"""
🧪 test_parser_factory.py — unit-тести для ParserFactory

Перевіряє:
- Коректне повернення BaseParser для продуктового URL
"""

from core.parsers.parser_factory import ParserFactory  # 🏭 Фабрика парсерів
from core.parsers.base_parser import BaseParser  # 📦 Базовий парсер

def test_get_parser_returns_base_parser():
    url = "https://www.youngla.com/products/sample-product"
    parser = ParserFactory.get_product_parser(url)

    # ✅ Перевіряємо, що повертається саме BaseParser
    assert isinstance(parser, BaseParser)