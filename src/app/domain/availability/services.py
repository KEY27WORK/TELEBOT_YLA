# app/domain/availability/services.py
"""
📦 services.py — Чистый доменный сервис для логики проверки доступности товара.

🔹 Ключевые обязанности:
- Агрегация данных о наличии товара из разных регионов.
- Группировка данных по цветам и размерам.
- Формирование единой структуры данных (DTO) с результатами.

❌ Этот модуль не делает сетевых запросов, не работает с кешем или файлами.
"""

# 🔠 Системные импорты
from typing import List, Dict, Tuple

# 🧩 Внутренние модули проекта
from .interfaces import IAvailabilityService, RegionStock, AvailabilityReport

# ==============================
# 🏛️ ГЛАВНЫЙ ДОМЕННЫЙ СЕРВИС
# ==============================

class AvailabilityService(IAvailabilityService):
    """💧 Доменный сервис, выполняющий чистые операции с данными о наличии."""

    def create_report(self, all_regions_data: List[RegionStock]) -> AvailabilityReport:
        """
        Главный метод, который принимает сырые данные из всех регионов
        и возвращает структурированный отчёт.
        """
        # 1. Группируем данные по регионам и собираем все возможные размеры
        availability_by_region, all_sizes_map = self._group_data(all_regions_data)

        # 2. Создаём общую карту наличия (если доступно хоть где-то -> True)
        merged_stock = self._merge_stock(all_regions_data)

        # 3. Возвращаем единый, чистый объект с результатами
        return AvailabilityReport(
            availability_by_region=availability_by_region,
            all_sizes_map=all_sizes_map,
            merged_stock=merged_stock,
        )

    def _group_data(self, all_regions_data: List[RegionStock]) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]]]:
        """
        Группирует данные для админ-отчёта и создаёт карту всех существующих размеров.
        Это чистая функция, работающая только со списками и словарями.
        """
        grouped: Dict[str, Dict[str, List[str]]] = {}
        all_sizes_map: Dict[str, List[str]] = {}

        for region_data in all_regions_data:
            for color, sizes in region_data.stock_data.items():
                for size, is_available in sizes.items():
                    # Собираем все уникальные размеры для каждого цвета
                    all_sizes_map.setdefault(color, [])
                    if size not in all_sizes_map[color]:
                        all_sizes_map[color].append(size)

                    # Если размер доступен, добавляем его в отчёт по этому региону
                    if is_available:
                        grouped.setdefault(color, {}).setdefault(region_data.region_code, []).append(size)
        return grouped, all_sizes_map

    def _merge_stock(self, all_regions_data: List[RegionStock]) -> Dict[str, Dict[str, bool]]:
        """
        Создаёт единую карту наличия для публичного отчёта.
        Размер считается доступным, если он есть хотя бы в одном регионе.
        """
        merged: Dict[str, Dict[str, bool]] = {}

        for region_data in all_regions_data:
            for color, sizes in region_data.stock_data.items():
                merged.setdefault(color, {})
                for size, is_available in sizes.items():
                    # Логика OR: если уже True, оставляем True. Если False, проверяем, доступен ли он сейчас.
                    merged[color][size] = merged[color].get(size, False) or is_available
        return merged