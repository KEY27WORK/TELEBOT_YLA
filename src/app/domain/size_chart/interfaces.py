# 📏 app/domain/size_chart/interfaces.py
"""
📏 Контракти для пошуку та обробки таблиць розмірів.

🔹 Визначає типи прогрес-івентів і callback, який повідомляє про стадії.
🔹 Описує протоколи `ISizeChartFinder` та `ISizeChartService` для різних реалізацій.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                     # 🧾 Логування ініціалізації протоколів
from dataclasses import dataclass, field                         # 🧱 Структури даних ProgressEvent
from enum import Enum                                              # 🎚️ Стадії обробки
from typing import (                                               # 🧰 Узагальнені типи
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    runtime_checkable,
)

# 🧩 Внутрішні модулі
from app.shared.utils.prompts import ChartType                     # 🧾 Тип таблиць розмірів


# ================================
# 🪵 ЛОГЕР МОДУЛЯ
# ================================
logger = logging.getLogger(__name__)                               # 🧾 Використовуємо ім'я модуля для domain-level логів
Url = str                                                          # 🌐 Простий аліас для URL


# ================================
# 🏷️ СТАДІЇ ОБРОБКИ
# ================================
class Stage(str, Enum):
    """Перелік етапів обробки таблиць розмірів (підходить для метрик/UX)."""

    QUEUED = "queued"                                               # 🅿️ Івент поставлено в чергу
    STARTED = "started"                                             # ▶️ Обробка почалася
    DONE = "done"                                                   # ✅ Обробка завершена (у тому числі з помилкою)


# ================================
# 📡 ПРОГРЕС-ІВЕНТ
# ================================
@dataclass(frozen=True)
class ProgressEvent:
    """Подія прогресу, яку відправляє сервіс під час обробки."""

    stage: Stage                                                    # 🎚️ Поточна стадія
    url: Optional[str] = None                                       # 🔗 Яку сторінку обробляємо
    chart_type: Optional[ChartType] = None                          # 📊 Тип таблиці (якщо відомий)
    error: Optional[str] = None                                     # ❌ Повідомлення про помилку (якщо є)


ProgressFn = Callable[[ProgressEvent], Awaitable[None]]            # 📣 Async callback прогресу


# ================================
# 🔍 ПРОТОКОЛ ПОШУКУ
# ================================
@runtime_checkable
class ISizeChartFinder(Protocol):
    """
    Контракт пошуку таблиць розмірів у HTML (розбір DOM/regex тощо).
    """

    def find_images(
        self,
        page_source: str,
        product_sku: Optional[str] = None,
    ) -> List[Tuple[Url, ChartType]]:
        """
        Повертає список пар (URL зображення, тип таблиці).

        Args:
            page_source: HTML-джерело сторінки.
            product_sku: Артикул товару (наприклад, "W542"), якщо відомий.
        """
        ...


# ================================
# 🚚 ПРОТОКОЛ СЕРВІСУ
# ================================
@runtime_checkable
class ISizeChartService(Protocol):
    """
    Контракт сервісу, що оркеструє повний цикл: пошук, OCR/генерація, відправка.
    """

    async def process_all_size_charts(
         self,
         page_source: str,
         product_sku: Optional[str] = None,
         on_progress: Optional[ProgressFn] = None,
    ) -> SizeChartArtifacts:
        """
        Повертає список шляхів до згенерованих таблиць (PNG/зображення).

        Args:
            page_source: HTML-код сторінки товару.
            product_sku: Артикул товару (наприклад, "W542"), якщо відомий.
            on_progress: Колбек прогресу.
        """
        ...


@dataclass
class SizeChartArtifacts:
    """📦 Результат пайплайна size-chart з розділенням на типи таблиць."""

    product_tables: List[str] = field(default_factory=list)
    global_tables: List[str] = field(default_factory=list)
    extra_tables: Dict[str, List[str]] = field(default_factory=dict)

    def register_product(self, path: str) -> None:
        self.product_tables.append(path)

    def register_global(self, path: str) -> None:
        self.global_tables.append(path)

    def register_extra(self, label: str, path: str) -> None:
        self.extra_tables.setdefault(label, []).append(path)

    @property
    def product_table(self) -> Optional[str]:
        return self.product_tables[0] if self.product_tables else None

    @property
    def global_table(self) -> Optional[str]:
        return self.global_tables[0] if self.global_tables else None

    def ordered_paths(self) -> List[str]:
        ordered: List[str] = []
        ordered.extend(self.product_tables)
        ordered.extend(self.global_tables)
        for paths in self.extra_tables.values():
            ordered.extend(paths)
        return ordered

    def as_dict(self) -> Dict[str, List[str]]:
        data: Dict[str, List[str]] = {
            "product": list(self.product_tables),
            "global": list(self.global_tables),
        }
        if self.extra_tables:
            data["extra"] = [path for paths in self.extra_tables.values() for path in paths]
        return data


logger.debug("🧭 Протоколи таблиць розмірів завантажено")          # 🧭 Фіксуємо факт ініціалізації
