""" 🧰 parser.py — модуль парсингу товарів і колекцій з сайту YoungLA.

🔹 Класи:
- `ProductParser` — визначає регіон і викликає відповідний парсер товару.
- `CollectionParser` — визначає регіон і викликає парсер колекцій.

Використовує:
- BaseParser для парсингу товару
- UniversalCollectionParser для парсингу колекції
- CurrencyManager для визначення регіону
- Логування для діагностики
"""

# 📦 Базові модулі
import logging
from typing import Optional

# 🧠 Парсери
from core.parsing.base_parser import BaseParser
from core.parsing.collections.universal_collection_parser import UniversalCollectionParser

# 💱 Валюта
from core.currency.currency_manager import CurrencyManager


class CollectionParser:
    """ 🧾 Менеджер парсингу колекцій:
    - Використовує UniversalCollectionParser
    """

    def __init__(self, url: str):
        self.url = url
        self.parser = UniversalCollectionParser(url)

    async def extract_product_links(self) -> list[str]:
        """
        🔗 Витягує список посилань на товари з колекції.

        :return: Список URL товарів
        """
        return await self.parser.extract_product_links()