"""
📦 availability_aggregator.py — агрегатор доступності товару по регіонах для YoungLA.

🔹 Клас:
- `AvailabilityAggregator` — асинхронно збирає дані по кожному регіону (US, EU, UK), обʼєднує та форматує доступність розмірів та кольорів.

Використовується:
- Внутрішньо у ProductHandler
- Формує фінальний вивід для Telegram-бота (обʼєднану наявність)
"""

# 📦 Стандартні
import asyncio
import logging

# 🧠 Парсинг
from core.parsing.base_parser import BaseParser
from core.parsing.json_ld_parser import JsonLdAvailabilityParser
from core.parsing.color_size_formatter import ColorSizeFormatter


class AvailabilityAggregator:
    """
    🧠 Основний агрегатор доступності товару:
    - Паралельно перевіряє всі регіони (US, EU, UK)
    - Агрегує кольори/розміри по всіх регіонах
    - Формує форматований результат для Telegram
    """

    # 🔗 Доменні URL по регіонам
    REGIONS = {
        "us": "https://www.youngla.com",
        "eu": "https://eu.youngla.com",
        "uk": "https://uk.youngla.com"
    }

    @staticmethod
    async def fetch_region_data(region_code: str, product_path: str):
        """
        🔄 Парсинг окремого регіону (US, EU, UK).

        :param region_code: Ключ регіону (us / eu / uk)
        :param product_path: URL path продукту без домену
        :return: Кортеж (region_code, stock_data)
        """
        url = f"{AvailabilityAggregator.REGIONS[region_code]}{product_path}"
        parser = BaseParser(url, enable_progress=False)
        success = await parser.fetch_page()
        if not success:
            logging.error(f"❌ Не вдалося завантажити сторінку для регіону {region_code}")
            return region_code, {}

        # 1️⃣ Основний парсинг через JSON-LD
        stock_data = JsonLdAvailabilityParser.extract_color_size_availability(parser.page_source)

        # 2️⃣ Якщо JSON-LD порожній — fallback по кольорам
        if not stock_data:
            colors = await parser.extract_colors_from_html()
            stock_data = {color: {} for color in colors}

        return region_code, stock_data

    @staticmethod
    async def aggregate_availability(product_path: str):
        """
        🔄 Агрегація наявності по всіх регіонах (повертає сирі дані по регіонах).

        :param product_path: URL path продукту
        :return: Словник {region: stock_data}
        """
        tasks = [
            AvailabilityAggregator.fetch_region_data(region_code, product_path)
            for region_code in AvailabilityAggregator.REGIONS
        ]

        results = await asyncio.gather(*tasks)
        aggregated = {region: stock for region, stock in results}
        aggregated["ua"] = {}  # Україна — завжди пусто

        return aggregated

    @staticmethod
    def merge_global_stock(aggregated: dict) -> dict:
        """
        🔄 Обʼєднання наявності з усіх регіонів в єдину фінальну картину.

        :param aggregated: Регіональні сирі дані
        :return: Обʼєднаний словник {color: {size: доступність (bool)}}
        """
        merged = {}

        for region_data in aggregated.values():
            for color, sizes in region_data.items():
                if color not in merged:
                    merged[color] = {}

                for size, available in sizes.items():
                    if size not in merged[color]:
                        merged[color][size] = False
                    merged[color][size] = merged[color][size] or available

        return merged
    
    @staticmethod
    async def aggregate_availability_formatted(product_path: str) -> str:
        """
        🔄 Фінальний форматований вивід в строку для Telegram.

        :param product_path: URL path продукту
        :return: Відформатований текст кольорів і розмірів
        """
        aggregated = await AvailabilityAggregator.aggregate_availability(product_path)
        merged = AvailabilityAggregator.merge_global_stock(aggregated)
        return ColorSizeFormatter.format_color_size_availability(merged)