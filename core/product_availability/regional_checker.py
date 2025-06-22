"""
🔹 Клас `RegionalAvailabilityChecker`:
- check_basic: короткий текстовий звіт по регіонах (✅/❌)
- check_full: повна карта наявності по регіонах (неагрегована)
- aggregate_availability: злиття даних усіх регіонів у єдину карту доступних розмірів
"""
import asyncio
from core.product_availability.availability_manager import AvailabilityManager

class RegionalAvailabilityChecker:
    @staticmethod
    async def check_basic(product_path: str) -> str:
        """
        📦 Швидка перевірка доступності товару по регіонах (US, EU, UK).
        Повертає короткий підсумок наявності у вигляді тексту з прапорцями.
        """
        manager = AvailabilityManager()
        # Використовуємо метод менеджера для швидкої перевірки
        return await manager.check_simple_availability(product_path)

    @staticmethod
    async def check_full(product_path: str) -> dict:
        """
        📊 Повний парсинг наявності через регіональні сайти.
        Повертає словник {region: {color: {size: bool}}} з даними по кожному регіону.
        """
        manager = AvailabilityManager()
        results = await manager.fetch_all_regions(product_path)
        # Перетворюємо список результатів на словник {region: stock_data}
        data_by_region = {region: stock for region, stock in results}
        return data_by_region

    @staticmethod
    def aggregate_availability(data: dict) -> dict:
        """
        🔗 Агрегує дані з усіх регіонів у єдину карту доступних розмірів.
        Наприклад, { "Black": ["M", "L"], "White": ["S"] } для розмірів, що є в наявності.
        :param data: Словник по регіонах: {region: {color: {size: bool}}}
        :return: Словник {color: [розміри, доступні хоча б в одному регіоні]}
        """
        aggregated_data: dict = {}
        # Проходимо регіони у фіксованому порядку для стабільності результату
        for region in ["us", "eu", "uk"]:
            if region in data:
                for color, sizes in data[region].items():
                    for size, available in sizes.items():
                        if available:
                            aggregated_data.setdefault(color, [])
                            if size not in aggregated_data[color]:
                                aggregated_data[color].append(size)
        return aggregated_data
