"""
📦 availability_manager.py — Клас керування для парсингу та агрегації даних про наявність товарів.

🔹 Клас:
- `AvailabilityManager` — мульти-регіональний парсер з fallback-логікою.
- Має швидку булеву перевірку доступності по регіонах.
- Форматує фінальний вивід для Telegram.
"""

# 📦 Стандартні бібліотеки
import logging
import asyncio
import re

# 🧠 Парсинг та агрегація
from core.parsing.base_parser import BaseParser                 # 🕸 Завантаження і базовий парсинг сторінок
from core.parsing.json_ld_parser import JsonLdAvailabilityParser  # 📜 Парсинг JSON-LD блоків для кольорів і розмірів
from core.parsing.color_size_formatter import ColorSizeFormatter    # 🎨 Форматування доступності у текст для Telegram


class AvailabilityManager:
    """
    🧠 Основний клас для обробки наявності товарів по регіонах:
    - Паралельно збирає дані по кольорах та розмірах (US, EU, UK)
    - Має швидку булеву перевірку товару в кожному регіоні
    - Повертає відформатований текст для Telegram
    """

    # 🔗 Доменні URL по регіонах
    REGIONS = {
        "us": "https://www.youngla.com",
        "eu": "https://eu.youngla.com",
        "uk": "https://uk.youngla.com"
    }

    async def check_and_aggregate(self, product_path: str) -> str:
        """
        🔄 Повна агрегація даних по кольорах і розмірах.

        :param product_path: Шлях до товару (без домену)
        :return: Відформатований текст доступності
        """
        try:
            aggregated_data = await self._aggregate_availability(product_path)
            formatted_text = ColorSizeFormatter.format_color_size_availability(aggregated_data)
            return formatted_text
        except Exception as e:
            logging.error(f"❌ Помилка при агрегації: {e}")
            return "❌ Помилка агрегації даних про наявність."

    async def check_simple_availability(self, product_path: str) -> str:
        """
        ✅ Швидка булева перевірка наявності товару по регіонах.

        :param product_path: Шлях до товару
        :return: Строка для Telegram з емодзі та статусами (✅/❌)
        """
        tasks = [
            self._check_region_simple(region_code, product_path)
            for region_code in self.REGIONS
        ]
        results = await asyncio.gather(*tasks)
        results.append("🇺🇦 - ❌")  # Україна — завжди відсутня
        return "\n".join(results)

    async def _check_region_simple(self, region_code: str, product_path: str) -> str:
        """
        🔍 Перевірка доступності товару в одному регіоні (булево).

        :param region_code: Код регіону (us/eu/uk)
        :param product_path: Шлях до товару
        :return: Строка з емодзі і статусом "✅" або "❌"
        """
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧"}
        url = f"{self.REGIONS[region_code]}{product_path}"
        try:
            parser = BaseParser(url, enable_progress=False)
            if not await parser.fetch_page():
                logging.warning(f"⚠️ Не вдалося завантажити сторінку для {region_code}")
                return f"{flags.get(region_code, region_code)} - ❌"

            is_available = await parser.is_product_available()
            logging.info(f"🌍 {flags.get(region_code, region_code)} — {'✅' if is_available else '❌'}")
            return f"{flags.get(region_code, region_code)} - {'✅' if is_available else '❌'}"
        except Exception as e:
            logging.error(f"❌ Помилка перевірки {region_code}: {e}")
            return f"{flags.get(region_code, region_code)} - ❌ (помилка)"

    async def _aggregate_availability(self, product_path: str) -> dict:
        """
        🔄 Внутрішній метод для агрегації кольорів і розмірів з fallback-логікою.

        :param product_path: Шлях до товару
        :return: Обʼєднаний словник {color: {size: bool}}
        """
        tasks = [
            self._fetch_region_data(region_code, product_path)
            for region_code in self.REGIONS
        ]
        results = await asyncio.gather(*tasks)
        merged = self._merge_global_stock({region: data for region, data in results if data})
        return merged

    async def _fetch_region_data(self, region_code: str, product_path: str) -> tuple:
        """
        📥 Отримання кольорів і розмірів з регіону з fallback на HTML.

        :param region_code: Код регіону
        :param product_path: Шлях до товару
        :return: Кортеж (region_code, stock_data)
        """
        url = f"{self.REGIONS[region_code]}{product_path}"
        parser = BaseParser(url, enable_progress=False)

        if not await parser.fetch_page():
            logging.warning(f"⚠️ Не вдалося завантажити сторінку для регіону {region_code}")
            return region_code, {}

        stock_data = JsonLdAvailabilityParser.extract_color_size_availability(parser.page_source)

        # Фолбек, якщо JSON-LD порожній — парсимо кольори з HTML
        if not stock_data:
            colors = await parser.extract_colors_from_html()
            stock_data = {color: {} for color in colors}

        return region_code, stock_data

    @staticmethod
    def _merge_global_stock(aggregated: dict) -> dict:
        """
        🔗 Обʼєднує наявність товарів з усіх регіонів в єдину картину.

        :param aggregated: Словник даних по регіонах
        :return: Обʼєднаний словник {color: {size: bool}}
        """
        merged = {}
        for region_data in aggregated.values():
            for color, sizes in region_data.items():
                merged.setdefault(color, {})
                for size, available in sizes.items():
                    merged[color][size] = merged[color].get(size, False) or available
        return merged