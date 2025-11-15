# 📦 app/domain/availability/services.py
"""
📦 services.py — Чистий доменний сервіс для логіки перевірки наявності товару.

🔹 Обов'язки:
- Агрегація даних про наявність з різних регіонів.
- Групування за кольорами та регіонами, побудова карти всіх розмірів.
- Формування структурованого DTO-звіту (`AvailabilityReport`).

❗ Примітка:
Модуль **не** виконує мережевих запитів і не працює з кешем/файлами — лише чисті перетворення
переданих структур даних (без побічних ефектів).
"""

from __future__ import annotations

# 🔠 Стандартні імпорти
import logging                                                        # 🧾 Логування всіх кроків сервісу
from collections import defaultdict                                    # 🧺 Накопичуємо дані по регіонах/кольорах
from typing import DefaultDict, Dict, List, Mapping, Set, Tuple        # 🧰 Типізація та контейнери

# 🧩 Доменні типи/DTO
from app.shared.utils.logger import LOG_NAME                           # 🏷️ Базове імʼя логера проєкту
from .interfaces import (                                              # 🧾 Контракти та DTO домену availability
    AvailabilityReport,
    Color,
    IAvailabilityService,
    RegionCode,
    RegionStock,
    Size,
)
from .sorting_strategies import SizeKey, default_size_sort_key         # 🧮 Сортування розмірів
from .status import AvailabilityStatus                                 # ✅ Enum: YES / NO / UNKNOWN


# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
MODULE_LOGGER_NAME: str = f"{LOG_NAME}.domain.availability.services"  # 🏷️ Іменований префікс логера
logger = logging.getLogger(MODULE_LOGGER_NAME)                         # 🧾 Модульний логер
logger.debug("📦 availability.services імпортовано")                   # 🚀 Фіксуємо ініціалізацію модуля


def _norm_key(value: str) -> str:
    """Проста нормалізація ключів (зрізаємо пробіли)."""

    normalized: str = (value or "").strip()                          # ✂️ Прибираємо пробіли/None
    logger.debug("🔑 _norm_key | raw=%r normalized=%r", value, normalized)  # 🧾 Трасуємо нормалізацію
    return normalized                                                  # 📤 Повертаємо очищене значення


class AvailabilityService(IAvailabilityService):
    """💧 Чисті операції з даними про наявність (без I/O, лише трансформації)."""

    # ---------- Публічний інтерфейс ----------
    def create_report(
        self,
        all_regions_data: List[RegionStock],
        *,
        size_key: SizeKey = default_size_sort_key,  # ключ сортування інʼєктується
    ) -> AvailabilityReport:
        """
        Приймає сирі дані по всіх регіонах і повертає структурований звіт.

        Args:
            all_regions_data: Список структур `RegionStock` з даними про наявність.
            size_key: Ключ сортування розмірів (стратегія). За замовчуванням — універсальна.

        Returns:
            AvailabilityReport: Агрегований звіт для UI/подальшої обробки.
        """
        logger.info("📥 create_report старт | regions=%d", len(all_regions_data))   # 🧾 Вхідні дані

        availability_by_region, all_sizes_map = self._group_data(all_regions_data, size_key)  # 🗺️ Групування даних
        merged_stock = self._merge_stock(all_regions_data, size_key)                           # 🧮 Зведена карта

        report = AvailabilityReport(                                                          # 🧾 Підсумковий DTO
            availability_by_region=availability_by_region,
            all_sizes_map=all_sizes_map,
            merged_stock=merged_stock,
        )
        logger.info("📤 create_report завершено | colors=%d", len(report.availability_by_region))  # ✅ Готовий звіт
        return report

    # ---------- Внутрішні методи ----------
    def _group_data(
        self,
        all_regions_data: List[RegionStock],
        size_key: SizeKey,
    ) -> Tuple[Dict[Color, Dict[RegionCode, List[Size]]], Dict[Color, List[Size]]]:
        """
        Будує:
          • `grouped`: {color: {region_code: [sizes_available_sorted_unique...]}}
          • `all_sizes_map`: {color: [all_known_sizes_sorted...]}

        Стабільність порядку: спершу збираємо у множини, потім сортуємо size_key.
        """
        grouped_sets: DefaultDict[Color, DefaultDict[RegionCode, Set[Size]]] = defaultdict(lambda: defaultdict(set))  # 🧺 Тимчасова структура
        sizes_acc: DefaultDict[Color, Set[Size]] = defaultdict(set)                # 📋 Глобальна множина розмірів
        logger.debug("🗂️ _group_data старт | regions=%d", len(all_regions_data))    # 🧾 Починаємо агрегацію

        for region_data in all_regions_data:                                        # 🔁 Проходимо всі регіони
            region: RegionCode = _norm_key(region_data.region_code)                 # 🌍 Нормалізуємо код регіону
            stock: Mapping[Color, Mapping[Size, AvailabilityStatus]] = region_data.stock_data or {}  # 🗃️ Дані регіону

            for color_raw, sizes in stock.items():                                  # 🔁 Проходимо кольори
                color = _norm_key(color_raw)                                        # 🎨 Нормалізуємо колір
                if not color:
                    continue                                                       # 🚫 Пропускаємо порожні ключі

                for size_raw, status in (sizes or {}).items():                      # 🔁 Проходимо розміри всередині кольору
                    size = _norm_key(size_raw)                                      # 📏 Нормалізуємо розмір
                    if not size:
                        continue                                                   # 🚫 Ігноруємо пусті значення

                    sizes_acc[color].add(size)                                     # 1️⃣ Відстежуємо всі відомі розміри

                    if status is AvailabilityStatus.YES:                           # 2️⃣ У регіон записуємо лише YES
                        grouped_sets[color][region].add(size)

        grouped: Dict[Color, Dict[RegionCode, List[Size]]] = {}                     # 🗺️ Підсумкова структура по регіонах
        for color, regions in grouped_sets.items():                                 # 🔁 Сортуємо колір → регіон
            grouped[color] = {}
            for region_code, size_set in regions.items():
                grouped[color][region_code] = sorted(size_set, key=size_key)        # 📊 Сортуємо списки розмірів

        all_sizes_map: Dict[Color, List[Size]] = {                                  # 📋 Повний перелік розмірів по кольорам
            color: sorted(size_set, key=size_key) for color, size_set in sizes_acc.items()
        }
        logger.debug("🗂️ _group_data завершено | colors=%d", len(grouped))          # ✅ Завершили агрегацію
        return grouped, all_sizes_map

    def _merge_stock(
        self,
        all_regions_data: List[RegionStock],
        size_key: SizeKey,
    ) -> Dict[Color, Dict[Size, AvailabilityStatus]]:
        """
        Створює єдину тристанову карту наявності:
        Правило для кожного (color, size) по всіх регіонах:
          • Якщо є хоча б один YES → YES
          • Інакше, якщо є хоча б один NO (і не було YES) → NO
          • Інакше → UNKNOWN
        """
        merged: Dict[Color, Dict[Size, AvailabilityStatus]] = {}                    # 🧱 Зведена мапа статусів
        logger.debug("🧮 _merge_stock старт | regions=%d", len(all_regions_data))    # 🧾 Починаємо злиття

        for region_data in all_regions_data:                                        # 🔁 Проходимо регіони
            stock: Mapping[Color, Mapping[Size, AvailabilityStatus]] = region_data.stock_data or {}  # 🗃️ Дані регіону

            for color_raw, sizes in stock.items():                                  # 🔁 Перебираємо кольори
                color = _norm_key(color_raw)                                        # 🎨 Нормалізація кольору
                if not color:
                    continue                                                       # 🚫 Пропускаємо порожні ключі

                dst = merged.setdefault(color, {})                                  # 📦 Мапа розмірів для кольору
                for size_raw, status in (sizes or {}).items():                      # 🔁 Перебираємо розміри
                    size = _norm_key(size_raw)                                      # 📏 Нормалізація розміру
                    if not size:
                        continue                                                   # 🚫 Пропускаємо порожні значення

                    prev = dst.get(size)                                            # 🔎 Минуле значення статусу

                    if prev is None:                                                # 🆕 Перша зустріч — записуємо статус
                        dst[size] = status
                        continue

                    if prev is AvailabilityStatus.YES or status is AvailabilityStatus.YES:
                        dst[size] = AvailabilityStatus.YES                          # ✅ YES домінує
                    elif prev is AvailabilityStatus.NO or status is AvailabilityStatus.NO:
                        dst[size] = AvailabilityStatus.NO                           # 🚫 NO перемагає UNKNOWN
                    else:
                        dst[size] = AvailabilityStatus.UNKNOWN                     # ❓ Залишаємо UNKNOWN

        for color in list(merged.keys()):                                           # 🔁 Детерміновано сортуємо розміри
            items = merged[color].items()                                           # 📋 Ітерабельна пара (size, status)
            merged[color] = {k: v for k, v in sorted(items, key=lambda kv: size_key(kv[0]))}  # 📊 Нова впорядкована мапа

        logger.debug("🧮 _merge_stock завершено | colors=%d", len(merged))           # ✅ Завершення процесу
        return merged
