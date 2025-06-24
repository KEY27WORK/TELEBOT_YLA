"""
📄 report_builder.py — Генератор форматованих звітів про наявність товару.

🔹 Клас `AvailabilityReportBuilder`:
- Формує зведені звіти по всіх регіонах
- Генерує public/admin формати наявності
- Виводить лог детального розподілу розмірів
"""

# 📦 Стандартні
import logging
from typing import List, Tuple, Dict

# 🧱 Форматування
from core.product_availability.formatter import ColorSizeFormatter


class AvailabilityReportBuilder:
    """
    📊 Генератор публічного та адмін-звітів на основі регіональних даних.
    """

    def __init__(self, formatter: ColorSizeFormatter):
        # Інʼєкція форматтера для генерації звітів
        self.formatter = formatter

    def build(self, region_results: List[Tuple[str, dict]]) -> Tuple[str, str, str]:
        """
        🛠 Формує тексти звітів по наявності товару.

        :param region_results: Список даних з кожного регіону [(region_code, stock_data)]
        :return: Кортеж (region_checks, public_format, admin_format)
        """
        # Групування та агрегація даних
        per_region, all_sizes_map = self._group_by_region(region_results)
        merged_stock = self._merge_global_stock({r: d for r, d in region_results if d})

        # Побудова рядка перевірки наявності з прапорцями
        region_lines = []
        for region, stock in region_results:
            available = any(True for sizes in stock.values() for avail in sizes.values() if avail)
            region_lines.append(f"{self.formatter.get_flag(region)} - {'✅' if available else '❌'}")
        region_lines.append(f"{self.formatter.get_flag('ua')} - ❌")

        # Формування звітів
        region_checks = "\n".join(region_lines)
        public_format = self.formatter.format_color_size_availability(merged_stock)
        admin_format = self.formatter.format_admin_availability(per_region, all_sizes_map)

        # Логування результатів
        logging.info("\ud83d\udcca Детальна карта наявності по регіонах:")
        for color, regions in per_region.items():
            logging.info(f"🎨 {color}")
            for region, sizes in regions.items():
                logging.info(f"  {region.upper()}: {', '.join(sizes) if sizes else '🚫'}")

        return region_checks, public_format, admin_format

    def _group_by_region(self, region_data: List[Tuple[str, dict]]) -> Tuple[Dict[str, Dict[str, list]], Dict[str, list]]:
        """
        ✅ Групує дані по кольорах і регіонах, а також зберігає порядок розмірів.

        :param region_data: Список [(region, stock_data)]
        :return: Кортеж (per_region, all_sizes_map)
        """
        grouped = {}
        all_sizes_map = {}
        for region, data in region_data:
            for color, sizes in data.items():
                for size, is_available in sizes.items():
                    # Додаємо до мапи всіх розмірів (з порядком)
                    if color not in all_sizes_map:
                        all_sizes_map[color] = []
                    if size not in all_sizes_map[color]:
                        all_sizes_map[color].append(size)
                    # Додаємо лише доступні розміри до групи по регіону
                    if is_available:
                        grouped.setdefault(color, {}).setdefault(region, []).append(size)
        return grouped, all_sizes_map

    def _merge_global_stock(self, regional_data: dict) -> dict:
        """
        🔗 Об'єднує наявність по регіонах у загальну картину.

        :param regional_data: Дані по регіонах: {region: {color: {size: bool}}}
        :return: Об'єднана структура: {color: {size: bool}}
        """
        merged = {}
        for region, stock in regional_data.items():
            for color, sizes in stock.items():
                merged.setdefault(color, {})
                for size, available in sizes.items():
                    merged[color][size] = merged[color].get(size, False) or available
        return merged