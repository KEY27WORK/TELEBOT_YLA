"""
📦 availability_manager.py — Клас для мульти-регіональної перевірки та агрегації даних про наявність товарів.

🔹 Клас `AvailabilityManager`:
- Паралельно перевіряє доступність товару в регіонах (US, EU, UK)
- Формує публічні та адмінські звіти з форматуванням
- Використовує окремі сервіси кешування та генерації звітів
"""

# 📦 Стандартні
import time
import logging
import asyncio
from typing import Tuple, List, Dict

# 🌐 Парсинг сторінок
from core.parsers.base_parser import BaseParser
from core.parsers.json_ld_parser import JsonLdAvailabilityParser

# 🧱 Форматування та сервіси
from core.product_availability.formatter import ColorSizeFormatter
from core.product_availability.cache_service import AvailabilityCacheService
from core.product_availability.report_builder import AvailabilityReportBuilder

class AvailabilityManager:
    """
    🧠 Основний клас для обробки наявності товарів по регіонах:
    - Паралельно збирає дані по кольорах та розмірах з декількох регіональних сайтів (US, EU, UK).
    - Має швидку булеву перевірку товару в кожному регіоні.
    - Агрегує та форматує дані для відображення.
    """
    REGIONS = {
        "us": "https://www.youngla.com",
        "eu": "https://eu.youngla.com",
        "uk": "https://uk.youngla.com"
    }
    CACHE_TTL = 300  # секунд кешування даних

    def __init__(self):
        # Ініціалізація кешу для результатів перевірки
        self.cache = AvailabilityCacheService()
        self.report_builder = AvailabilityReportBuilder(formatter=ColorSizeFormatter())

    async def check_simple_availability(self, product_path: str) -> str:
        """
        ✅ Швидка булева перевірка наявності товару по регіонах.
        :param product_path: Шлях до товару (починаючи з '/products/...')
        :return: Рядок зі статусами наявності по регіонах (наприклад, "🇺🇸 - ✅ ...")
        """
        cached = self.cache.get(product_path, self.CACHE_TTL)
        if cached:
            return cached['region_checks']

        tasks = [self._check_region_simple(region_code, product_path) for region_code in self.REGIONS]
        results = await asyncio.gather(*tasks)
        results.append("🇺🇦 - ❌")  # Україна — завжди ❌
        summary = "\n".join(results)

        self.cache.set(product_path, {"region_checks": summary})
        return summary


    async def _check_region_simple(self, region_code: str, product_path: str) -> str:
        """
        🔍 Перевірка доступності товару в одному регіоні (тільки True/False).
        Повертає рядок з прапорцем регіону та статусом "✅" або "❌".
        """
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧"}
        url = f"{self.REGIONS[region_code]}{product_path}"
        try:
            parser = BaseParser(url, enable_progress=False)
            if not await parser.fetch_page():
                logging.warning(f"⚠️ Не вдалося завантажити сторінку для регіону {region_code} (URL: {url})")
                return f"{flags.get(region_code, region_code.upper())} - ❌"
            is_available = await parser.is_product_available()
            logging.info(f"{flags.get(region_code, region_code.upper())} — {'✅' if is_available else '❌'}")
            return f"{flags.get(region_code, region_code.upper())} - {'✅' if is_available else '❌'}"
        except Exception as e:
            logging.error(f"❌ Помилка перевірки регіону {region_code} (URL: {url}): {e}")
            return f"{flags.get(region_code, region_code.upper())} - ❌ (помилка)"

    async def _fetch_region_data(self, region_code: str, product_path: str) -> Tuple[str, dict]:
        """
        📥 Завантажує сторінку регіонального сайту та витягує дані про наявність кольорів/розмірів.
        Повертає кортеж (region_code, stock_data).
        """
        url = f"{self.REGIONS[region_code]}{product_path}"
        parser = BaseParser(url, enable_progress=False)
        if not await parser.fetch_page():
            logging.warning(f"⚠️ Не вдалося завантажити сторінку для регіону {region_code}")
            return region_code, {}
        # Отримуємо дані про наявність товару (колір->розміри->bool) через BaseParser
        stock_data = await parser.get_stock_data()
        return region_code, stock_data

    @staticmethod
    def _merge_global_stock(regional_data: dict) -> dict:
        """
        🔗 Об'єднує дані про наявність з різних регіонів в один словник.
        Якщо розмір доступний в будь-якому регіоні, вважаємо його доступним загалом.
        :param regional_data: {region: {color: {size: bool}}}
        """
        merged = {}
        for region, stock in regional_data.items():
            for color, sizes in stock.items():
                merged.setdefault(color, {})
                for size, available in sizes.items():
                    # Встановлюємо True, якщо хоч в одному регіоні доступно
                    merged[color][size] = merged[color].get(size, False) or available
        return merged

    async def fetch_all_regions(self, product_path: str) -> List[Tuple[str, dict]]:
        """
        📦 Паралельно отримує детальні дані про наявність з усіх регіонів (US, EU, UK).
        :return: Список кортежів [(region_code, stock_data), ...]
        """
        tasks = [self._fetch_region_data(region_code, product_path) for region_code in self.REGIONS]
        return await asyncio.gather(*tasks)

    def _group_by_region(self, region_data: List[Tuple[str, dict]]) -> Tuple[Dict[str, Dict[str, list]], Dict[str, list]]:
        """
        🔁 Трансформує сирі дані з регіонів у дві структури:
        - per_region: {color: {region: [sizes_available]}}
        - all_sizes_map: {color: [усі розміри]} (в порядку першої появи)
        """
        grouped = {}
        all_sizes_map = {}
        for region, data in region_data:
            for color, sizes in data.items():
                for size, is_available in sizes.items():
                    # Додаємо розмір до загальної мапи (уникаємо дублювання, зберігаємо порядок)
                    if color not in all_sizes_map:
                        all_sizes_map[color] = []
                    if size not in all_sizes_map[color]:
                        all_sizes_map[color].append(size)
                    # Якщо розмір доступний, додаємо до групованої структури per_region
                    if is_available:
                        grouped.setdefault(color, {}).setdefault(region, []).append(size)
        return grouped, all_sizes_map

    async def get_availability_report(self, product_path: str) -> Tuple[str, str, str]:
        """
        📊 Виконує повну перевірку товару по регіонах та формує звіти.
        :return: Кортеж (region_checks, public_format, admin_format)
        """
        cached = self.cache.get(product_path, self.CACHE_TTL)
        if cached and all(k in cached for k in ("region_checks", "public_format", "admin_format")):
            return cached['region_checks'], cached['public_format'], cached['admin_format']

        results = await self.fetch_all_regions(product_path)
        region_checks, public_format, admin_format = self.report_builder.build(results)

        self.cache.set(product_path, {
            "region_checks": region_checks,
            "public_format": public_format,
            "admin_format": admin_format
        })
        return region_checks, public_format, admin_format