""" 🧰 parser.py — модуль парсингу товарів і колекцій з сайту YoungLA.

🔹 Класи:
- `ProductParser` — визначає регіон і викликає відповідний парсер товару.
- `CollectionParser` — визначає регіон і викликає парсер колекцій.

Використовує:
- UniversalProductParser для парсингу товару
- UniversalCollectionParser для парсингу колекції
- CurrencyManager для визначення регіону
- Логування для діагностики
"""

# 📦 Базові модулі
import logging
from typing import Optional

# 🧠 Парсери
from core.parsing.products.universal_product_parser import UniversalProductParser
from core.parsing.collections.universal_collection_parser import UniversalCollectionParser

# 💱 Валюта
from core.currency.currency_manager import CurrencyManager


class ProductParser:
    """ 📦 Менеджер парсингу товару:
    - Визначає регіон за URL
    - Ініціалізує відповідний парсер
    - Повертає детальну інформацію про товар
    """

    def __init__(self, url: str):
        self.url = url
        self.region = self._detect_region(url)
        self.currency_manager = CurrencyManager(self.region)
        self.parser = self._select_parser()
        self.page_source: Optional[str] = None  # 🔄 Для сумісності зі старим кодом

    def _detect_region(self, url: str) -> str:
        """ 🌍 Визначає валюту/регіон за URL.

        :param url: Посилання на товар.
        :return: "USD", "EUR" або "GBP"
        """
        if ".com" in url and "eu." not in url and "uk." not in url:
            return "USD"
        elif "eu." in url:
            return "EUR"
        elif "uk." in url:
            return "GBP"
        else:
            raise ValueError(f"❌ Невідомий регіон для URL: {url}")

    def _select_parser(self):
        """ 🔁 Обирає відповідний парсер."""
        return UniversalProductParser(self.url)

    async def get_product_info(self):
        """ 📥 Асинхронно повертає всі дані про товар як кортеж.

        :return: (title, price, description, image_url, weight, colors_text, images, currency)
        """
        try:
            data = await self.parser.parse()
            logging.info(f"✅ Данні з {self.parser.__class__.__name__}: {data}")
            self.page_source = getattr(self.parser, "page_source", None)

            # 🧩 Базові поля
            title = str(data.get("title", "Нет названия"))
            description = str(data.get("description", "Нет описания"))
            image_url = str(data.get("main_image", ""))
            colors_sizes = str(data.get("colors_sizes", ""))
            currency = str(data.get("currency", "USD"))
            images = data.get("images", [])

            # 💰 Ціна
            try:
                price = float(data.get("price", 0.0))
            except (TypeError, ValueError):
                logging.warning("⚠️ Не вдалося перетворити ціну у float")
                price = 0.0

            # ⚖️ Вага
            try:
                weight = float(data.get("weight", 0.5))
            except (TypeError, ValueError):
                logging.warning("⚠️ Не вдалося перетворити вагу у float")
                weight = 0.5

            # ✅ Підсумковий лог
            logging.info(
                f"📦 Отримано товар: {title}, ціна: {price}, вага: {weight}, валюта: {currency}"
            )
            logging.info(
                "📄 Контент: title: %s; \nprice: %s; \ndescription: %s; \nimage: %s; \nweight: %s; \ncolors: %s; \nimages: %d",
                title, price, description, image_url, weight, colors_sizes, len(images)
            )

            return title, price, description, image_url, weight, colors_sizes, images, currency

        except Exception as e:
            logging.exception(f"❌ Помилка при парсингу товару: {e}")
            return "Помилка", 0.0, "Помилка", "", 0.5, "", [], "USD"


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
