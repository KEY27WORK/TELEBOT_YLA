"""
📦 availability_manager.py — Клас для мульти-регіональної перевірки та агрегації даних про наявність товарів.
"""

import logging
import asyncio
import time
from typing import Tuple, List, Dict

from core.parsers.base_parser import BaseParser
from core.parsers.json_ld_parser import JsonLdAvailabilityParser
from core.product_availability.formatter import ColorSizeFormatter


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
        self._cache: Dict[str, dict] = {}

    async def check_simple_availability(self, product_path: str) -> str:
        """
        ✅ Швидка булева перевірка наявності товару по регіонах.
        :param product_path: Шлях до товару (починаючи з '/products/...')
        :return: Рядок зі статусами наявності по регіонах (наприклад, "🇺🇸 - ✅ ...")
        """
        # Перевіряємо кеш, щоб уникнути зайвих запитів
        if product_path in self._cache:
            cached = self._cache[product_path]
            if time.time() - cached.get('time', 0) < self.CACHE_TTL:
                return cached['region_checks']

        tasks = [self._check_region_simple(region_code, product_path) for region_code in self.REGIONS]
        results = await asyncio.gather(*tasks)
        results.append("🇺🇦 - ❌")  # Україна — завжди відсутня (немає окремого сайту)
        summary = "\n".join(results)
        # Кешуємо результат швидкої перевірки окремо (без детальних даних)
        self._cache[product_path] = {
            'time': time.time(),
            'region_checks': summary
        }
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
                logging.warning(f"⚠️ Не вдалося завантажити сторінку для регіону {region_code}")
                return f"{flags.get(region_code, region_code.upper())} - ❌"
            is_available = await parser.is_product_available()
            logging.info(f"{flags.get(region_code, region_code.upper())} — {'✅' if is_available else '❌'}")
            return f"{flags.get(region_code, region_code.upper())} - {'✅' if is_available else '❌'}"
        except Exception as e:
            logging.error(f"❌ Помилка перевірки регіону {region_code}: {e}")
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

    async def _aggregate_availability(self, product_path: str) -> dict:
        """
        🔄 Агрегація наявності товару з усіх регіонів у єдину карту.
        Повертає словник {color: {size: bool}}, де True означає, що розмір є хоча б в одному регіоні.
        """
        tasks = [self._fetch_region_data(region_code, product_path) for region_code in self.REGIONS]
        results = await asyncio.gather(*tasks)
        # Об'єднуємо усі дані по регіонах
        merged_stock = self._merge_global_stock({region: data for region, data in results if data})
        return merged_stock

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
        results = await asyncio.gather(*tasks)
        return results

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

    def _merge_available_sizes(self, per_region: Dict[str, Dict[str, list]], all_sizes_map: Dict[str, list]) -> Dict[str, list]:
        """
        🔗 Формує словник {color: [available_sizes]} для публічного виводу.
        Зберігає початковий порядок розмірів.
        """
        merged_data = {}
        for color in all_sizes_map:
            sizes_in_order = list(all_sizes_map[color])
            logging.info(f"всі розміри {sizes_in_order}")  # Debug: список усіх розмірів для {color}
            available_sizes = []
            for size in sizes_in_order:
                # Додаємо розмір, якщо він присутній хоча б в одному регіоні
                if any(size in per_region.get(color, {}).get(region, []) for region in per_region.get(color, {})):
                    available_sizes.append(size)
            merged_data[color] = available_sizes
        return merged_data

    def _get_public_format(self, merged_data: Dict[str, list]) -> str:
        """
        🖼 Форматує публічний список кольорів і доступних розмірів для Telegram.
        :param merged_data: {color: [список доступних розмірів]}
        """
        return "\n".join([
            f"• {color}: {', '.join(sizes)}" if sizes else f"• {color}: 🚫"
            for color, sizes in merged_data.items()
        ])

    async def get_availability_report(self, product_path: str) -> Tuple[str, str, str]:
        """
        📊 Виконує повну перевірку товару по регіонах та формує звіти.
        :return: Кортеж (region_checks, public_format, admin_format)
        """
        # Перевірка кешу
        if product_path in self._cache:
            cached = self._cache[product_path]
            if time.time() - cached.get('time', 0) < self.CACHE_TTL:
                return cached['region_checks'], cached['public_format'], cached['admin_format']

        # Паралельно отримуємо дані з усіх регіонів
        results = await self.fetch_all_regions(product_path)
        # Формуємо рядок швидкої перевірки по регіонах (✅/❌)
        flag_map = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧"}
        region_lines = []
        for region, stock in results:
            # Визначаємо, чи є товар в наявності в цьому регіоні
            available = any(True for sizes in stock.values() for avail in sizes.values() if avail)
            region_lines.append(f"{flag_map.get(region, region.upper())} - {'✅' if available else '❌'}")
        region_lines.append("🇺🇦 - ❌")
        region_checks = "\n".join(region_lines)
        # Групуємо дані по регіонах і об'єднуємо розміри
        per_region, all_sizes_map = self._group_by_region(results)
        merged_data = self._merge_available_sizes(per_region, all_sizes_map)
        public_format = self._get_public_format(merged_data)
        admin_format = ColorSizeFormatter.format_admin_availability(per_region, all_sizes_map)
        # Логування детальної карти по регіонах
        logging.info("📊 Детальна карта наявності по регіонах:")
        for color, regions in per_region.items():
            logging.info(f"🎨 {color}")
            for region, sizes in regions.items():
                logging.info(f"  {region.upper()}: {', '.join(sizes) if sizes else '🚫'}")
        # Збереження в кеш
        self._cache[product_path] = {
            'time': time.time(),
            'region_checks': region_checks,
            'public_format': public_format,
            'admin_format': admin_format
        }
        return region_checks, public_format, admin_format
