# 🔎 app/infrastructure/size_chart/youngla_finder.py
"""
🔎 Пошук таблиць розмірів на сторінках YoungLA.

🔹 Аналізує HTML (DOM + JSON-LD) і знаходить посилання на зображення size-chart.
🔹 Класифікує таблиці за типами (`ChartType`) для подальшої генерації.
🔹 Нормалізує URL, уникає дублікатів і застосовує евристики/атрибути.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging
from typing import Iterator, List, Optional, Set, Tuple

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup
from bs4.element import PageElement, Tag

# 🧩 Внутрішні модулі проєкту
from app.domain.size_chart.interfaces import ISizeChartFinder, Url
from app.infrastructure.size_chart.table_generator_factory import CHART_TYPE_PRIORITY
from app.shared.utils.logger import LOG_NAME
from app.shared.utils.prompts import ChartType

__all__ = ["YoungLASizeChartFinder"]

logger = logging.getLogger(f"{LOG_NAME}.sizefinder")  # 🪵 Іменований логер


# ================================
# 🧾 ПРАВИЛА КЛАСИФІКАЦІЇ
# ================================
_UNIQUE_HITS: Tuple[str, ...] = (
    "size_chart",
    "size-chart",
    "sizechart",
    "_size_",
    "size_",
    "sizechartmen",
    "mens-size-chart",
    "men-size-chart",
)  # 🧬 Унікальні таблиці (чоловічі/загальні)

_GENERAL_HITS: Tuple[str, ...] = (
    "women-size-chart",
    "womens-size-chart",
    "women_size_chart",
    "ylafh-size-chart",
    "size_chart_top_jogger_",
)  # 👩‍🦰 Таблиці для жіночих товарів

_GRID_HITS: Tuple[str, ...] = ("grid", "size-grid", "size_grid")  # 🗺️ Заготовки для сіток зріст×вага

_ATTR_HINTS_UNIQUE: Tuple[str, ...] = ("data-size-chart", "data-size", "data-sizes")  # 🏷️ Атрибути унікальних таблиць
_ATTR_HINTS_GENERAL: Tuple[str, ...] = ("data-women-size", "data-women-chart")        # 🏷️ Атрибути жіночих таблиць


# ================================
# 🔧 ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _first_truthy(*values: object) -> Optional[str]:
    """Повертає перше непорожнє рядкове значення із набору."""
    for value in values:
        if isinstance(value, str):
            cleaned = value.strip()                                      # ✂️ Обрізаємо зайві пробіли
            if cleaned:
                return cleaned                                           # 🔁 Повертаємо знайдене значення
        elif isinstance(value, list):                                   # 🔁 Іноді BeautifulSoup повертає список значень
            for item in value:
                if isinstance(item, str):
                    cleaned_item = item.strip()                         # ✂️ Нормалізуємо елемент списку
                    if cleaned_item:
                        return cleaned_item                             # 🔁 Віддаємо перший валідний елемент
    return None                                                         # ⛔ Якщо валідних значень немає


def _attr_str(tag: Tag, key: str) -> Optional[str]:
    """Безпечно приводить значення атрибуту `tag[key]` до Optional[str]."""
    try:
        return _first_truthy(tag.get(key))                              # type: ignore[arg-type]  # 🧰 Фільтруємо до першого непорожнього значення
    except Exception:  # noqa: BLE001
        return None


def _normalize_url(raw: str) -> str:
    """Нормалізує URL: `//cdn` → `https://cdn`, порожні значення ігноруються."""
    cleaned = (raw or "").strip()                                       # 🧼 Прибираємо пробіли та None
    if not cleaned:
        return cleaned                                                  # ⛔ Повертаємо порожнє значення без змін
    if cleaned.startswith("//"):
        logger.debug("🌐 Нормалізуємо протокол-незалежний URL: %s", cleaned)
        return f"https:{cleaned}"                                       # 🌐 Додаємо HTTPS до протокол-незалежних URL
    return cleaned                                                      # 🔁 Повертаємо нормалізоване посилання


def _from_srcset(srcset: str) -> List[str]:
    """Повертає список URL із атрибуту `srcset` (беремо перший елемент кожної пари)."""
    urls: List[str] = []                                                # 📦 Колекція кандидатів
    for part in (srcset or "").split(","):
        candidate = part.strip().split(" ", 1)[0].strip()               # 🔍 Беремо URL без суфіксів ширини/щільності
        if candidate:
            urls.append(candidate)                                      # ➕ Додаємо валідний варіант
    return urls                                                         # 📤 Повертаємо список URL


def _img_src_candidates(img: Tag) -> Iterator[str]:
    """
    Генерує всі можливі URL для зображення:
    • атрибути `src`, `data-*`, `srcset`, `data-srcset`
    • `<picture><source ...>` із різними варіантами srcset.
    Повертає унікальні значення у порядку знаходження.
    """
    seen: Set[str] = set()                                              # 🧾 Відстежуємо вже повернуті URL

    def _yield_unique(candidate: Optional[str]) -> Iterator[str]:
        """Віддає кандидат лише один раз (дедуплікація)."""
        if not candidate:
            return
        normalized = candidate.strip()                                  # ✂️ Очищаємо кандидат перед перевіркою
        if not normalized or normalized in seen:
            return
        seen.add(normalized)                                            # 🧷 Запам'ятовуємо, щоб не дублювати
        yield normalized                                                # 📤 Повертаємо унікальне значення

    # 🖼️ Основні атрибути <img>
    for key in ("src", "data-src", "data-original", "data-lazy", "data-zoom-image"):
        for value in _yield_unique(_attr_str(img, key)):                # 🔍 Перебираємо атрибути один за іншим
            yield value                                                 # 📤 Повертаємо знайдені URL

    # 🖼️ Атрибути srcset/data-srcset
    for key in ("srcset", "data-srcset"):
        srcset_value = _attr_str(img, key)                              # 📡 Зчитуємо атрибут із набором URL
        if srcset_value:
            for url in _from_srcset(srcset_value):
                for value in _yield_unique(url):                        # ♻️ Дедуплікуємо кожен знайдений URL
                    yield value

    # 🖼️ Якщо <img> всередині <picture> — враховуємо <source>
    parent: Optional[PageElement] = img.parent                          # 🧬 Перевіряємо контекст батьківського вузла
    if isinstance(parent, Tag) and parent.name == "picture":
        for source in parent.find_all("source"):
            if not isinstance(source, Tag):
                continue
            for key in ("srcset", "data-srcset"):
                srcset_value = _attr_str(source, key)                   # 🧾 Збираємо srcset із <source>
                if srcset_value:
                    for url in _from_srcset(srcset_value):
                        for value in _yield_unique(url):                # ♻️ Повертаємо лише нові значення
                            yield value


def _classify(url_lower: str, img_tag: Tag) -> Optional[ChartType]:
    """
    Визначає тип таблиці (`ChartType`) на основі URL та атрибутів.
    Порядок перевірок: строгі хіт-листи → data-атрибути → alt/title.
    """
    # 📌 Строгі хіти за URL
    if any(hit in url_lower for hit in _GENERAL_HITS):
        return ChartType.GENERAL
    if any(hit in url_lower for hit in _UNIQUE_HITS) and "women-size-chart" not in url_lower:
        return ChartType.UNIQUE
    if any(hit in url_lower for hit in _GRID_HITS):
        return ChartType.UNIQUE_GRID

    # 🏷️ Евіристики за data-атрибутами
    for key in _ATTR_HINTS_UNIQUE:
        if img_tag.has_attr(key):                                       # 🏷️ Унікальні таблиці позначаються data-атрибутами
            return ChartType.UNIQUE
    for key in _ATTR_HINTS_GENERAL:
        if img_tag.has_attr(key):                                       # 🏷️ Жіночі таблиці часто мають спеціальні мітки
            return ChartType.GENERAL

    # 🔍 Alt/title як слабкі сигнали
    alt_title = (
        _first_truthy(_attr_str(img_tag, "alt"), _attr_str(img_tag, "title")) or ""
    ).lower()                                                           # 🔍 Аналізуємо текстові підказки (alt/title)
    if alt_title:
        if "size" in alt_title and "women" not in alt_title:
            return ChartType.UNIQUE                                     # 🧍 Загальні / чоловічі таблиці
        if "women" in alt_title and "size" in alt_title:
            return ChartType.GENERAL                                    # 👩 Жіночі таблиці
        if "grid" in alt_title and "size" in alt_title:
            return ChartType.UNIQUE_GRID                                # 🗺️ Таблиці-сітки (height/weight)

    return None                                                         # ❔ Тип не визначено


# ================================
# 🔎 ОСНОВНИЙ КЛАС
# ================================
class YoungLASizeChartFinder(ISizeChartFinder):
    """Знаходить зображення size-chart на сторінках YoungLA та визначає їх тип."""

    def __init__(self) -> None:
        logger.debug("🔎 YoungLASizeChartFinder ініціалізований.")

    def find_images(self, page_source: str) -> List[Tuple[Url, ChartType]]:
        """
        Повертає список `(url, ChartType)` — відсортований за пріоритетом.

        Args:
            page_source: HTML-джерело сторінки (повинно бути непорожнім).
        """
        if not isinstance(page_source, str) or not page_source.strip():          # 🛡️ Валідація вхідних даних
            logger.warning("⚠️ Порожній page_source для YoungLASizeChartFinder")
            return []

        logger.info("🔎 Пошук size-chart: довжина HTML=%d символів.", len(page_source))
        soup = BeautifulSoup(page_source, "html.parser")                         # 🍲 Парсимо HTML

        # 📦 Беремо типові блоки з інформацією про товар, далі fallback — увесь документ
        blocks: List[Tag] = [
            block for block in soup.select(".product-info__block-item") if isinstance(block, Tag)
        ]
        extra_info = soup.select_one("#product-extra-information")
        if isinstance(extra_info, Tag):
            blocks.append(extra_info)                                            # 🔁 Додаємо додатковий блок
        if not blocks:
            blocks = [soup]                                                      # 🆘 Фолбек: переглядаємо всю сторінку
        logger.debug("📦 Кількість оброблюваних блоків: %d", len(blocks))

        found: List[Tuple[Url, ChartType]] = []                                  # 📦 Результати
        seen: Set[str] = set()                                                   # 🚫 Уникнення дублікатів

        for block in blocks:
            logger.debug("🔍 Аналізуємо блок з %d img.", len(block.find_all('img')))
            for el in block.find_all("img"):                                     # 🔍 Шукаємо всі <img> у блоці
                if not isinstance(el, Tag):
                    continue
                img: Tag = el

                candidates = list(_img_src_candidates(img))                      # 🔄 Збираємо всі кандидати URL
                if not candidates:
                    logger.debug("⏭️ Img без кандидатів src/srcset (attrs=%s).", img.attrs)
                    continue

                for raw in candidates:
                    url = _normalize_url(raw)                                    # 🌐 Нормалізуємо протокол
                    if not url or url in seen:                                   # 🛑 Пропускаємо порожні/дубльовані
                        continue

                    chart_type = _classify(url.lower(), img)                     # 🧮 Спробуємо визначити тип
                    if chart_type is None:
                        seen.add(url)                                            # 📌 Не size-chart → ігноруємо надалі
                        continue

                    found.append((url, chart_type))                              # ✅ Додаємо результат
                    logger.debug("✅ Знайдено size-chart (%s) → %s", chart_type.value, url)
                    seen.add(url)

        # 📊 Стабілізуємо видачу: спочатку UNIQUE → GENERAL → GRID
        found.sort(key=lambda item: CHART_TYPE_PRIORITY.get(item[1], 999))

        logger.info("🔎 Знайдено %d зображень size-chart", len(found))
        return found
