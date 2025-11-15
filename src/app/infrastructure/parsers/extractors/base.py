# 🧾 app/infrastructure/parsers/extractors/base.py
"""
🧾 Абстракції для конфігурації парсерів та екстракторів.

🔹 Кешує селектори з YAML та конфігів брендів.
🔹 Нормалізує текстові дані й посилання для екстракторів.
🔹 Експортує Selectors, _ConfigSnapshot та утиліти для mixin-класів.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import yaml	# 📄 Зчитуємо YAML-файли
from bs4 import BeautifulSoup	# 🥣 Парсимо HTML-документи
from bs4.element import NavigableString, PageElement, Tag	# 🧱 Типи DOM-вузлів

# 🔠 Системні імпорти
import importlib.resources as pkg_resources	# 📦 Доступ до ресурсів пакету
import json	# 🧾 Серіалізація та десеріалізація JSON
import logging	# 🧾 Логування подій
import re	# 🧵 Робота з регулярними виразами
from dataclasses import dataclass	# 🧱 Створення датакласів
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, cast	# 🧰 Типи для статичного аналізу

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService	# ⚙️ Доступ до конфігурацій
from app.shared.utils.collections import uniq_keep_order	# ♻️ Унікалізуємо послідовності
from app.shared.utils.logger import LOG_NAME	# 🏷️ Базова назва логера

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.parser.extractor")	# 🧾 Логер для екстракторів парсера

# ================================
# 📦 КОНСТАНТИ МОДУЛЯ
# ================================
_DEFAULT_SELECTORS: Dict[str, Any] = {
    "TITLE_LIST": (
        "h1.product-title",
        "h1.product__title",
        "h1[itemprop='name']",
        "meta[property='og:title']",
        "title",
    ),
    "PRICE_LIST": (
        ".price__current, .price--large, .product__price .price",
        ".product-price, .sale-price, .price-item--regular, .price-item--sale",
        "meta[itemprop='price']",
    ),
    "MAIN_IMAGE_LIST": (
        'meta[property="og:image"]',
        ".product__media img[src], .product-gallery__image img[src]",
        "img#FeaturedMedia-product-template[src]",
    ),
    "ALL_IMAGES_LIST": (
        ".product-gallery__thumbnail img[src]",
        ".product__media img[src]",
        ".product-gallery__thumbnail-list img[src]",
        "img[srcset], img[data-src], img[data-srcset], img[src]",
    ),
    "DESCRIPTION_CONTAINER_LIST": (
        'div[data-block-type="description"] .prose',
        "div.product__description, div#ProductAccordion-product-description .prose",
        "div#product-description, section.product-description, .rte.product__description, .prose",
    ),
    "JSON_LD_SCRIPT": 'script[type="application/ld+json"]',
    "LEGACY_STOCK_SELECTORS": (
        "script#ProductJson",
        'script[data-product-json="true"]',
        "script",
    ),
}	# 🧾 Базовий набір CSS-селекторів за замовчуванням

_FALLBACK_KEY_MAP: Dict[str, str] = {
    "MATERIAL": "Material",
    "MATERIALS": "Material",
    "FABRIC": "Material",
    "FIT": "Fit",
    "DESIGN": "Description",
    "DESCRIPTION": "Description",
    "MODEL": "Model",
    "MODELS": "Model",
    "FABRIC WEIGHT": "Fabric weight",
    "CARE": "Care",
    "FEATURES": "Features",
    "DETAILS": "Details",
}	# 🔁 Карта ключів для fallback у різних локалях

# ================================
# 🛠️ ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _norm_ws(text: str) -> str:
    """Нормалізує пробіли у переданому рядку."""
    if not text:	# 🚫 Порожній або None рядок
        return ""	# 🪣 Повертаємо порожній результат
    return re.sub(r"\s+", " ", text).strip()	# 🧹 Стискаємо та обрізаємо пробіли


def _attr_to_str(value: Any) -> str:
    """Повертає перше непорожнє текстове значення атрибута."""
    if value is None:	# 🚫 Атрибут відсутній
        return ""	# 🪣 Порожній рядок
    if isinstance(value, (list, tuple)):	# 📚 Атрибут представлено колекцією
        for candidate in value:	# 🔁 Перебираємо можливі значення
            if candidate:	# ✅ Обираємо перший непорожній елемент
                return str(candidate)	# 🔄 Повертаємо текстове представлення
        return ""	# 🪣 Жодного валідного значення
    return str(value)	# 🔄 Конвертуємо одиночний атрибут у рядок


def _as_list(x: Any) -> List[Any]:
    """Гарантує отримання списку елементів."""
    if x is None:	# 🚫 Значення відсутнє
        return []	# 📦 Повертаємо порожній список
    if isinstance(x, list):	# 📚 Вже список
        return x	# 🔁 Використовуємо як є
    return [x]	# 📦 Загортаємо значення у список


def _try_json_loads(raw: str) -> Optional[Any]:
    """Безпечно десеріалізує JSON, повертаючи None у разі помилок."""
    raw_clean = (raw or "").strip()	# 🧼 Прибираємо зайві пробіли
    if not raw_clean:	# 🚫 Порожній рядок
        return None	# 🪣 Немає що парсити
    try:	# 🧪 Пробуємо розібрати JSON
        return json.loads(raw_clean)	# 📥 Десеріалізуємо у Python-структуру
    except Exception as exc:	# ⚠️ Некоректний формат JSON
        logger.debug("🐛 Помилка декодування JSON: %s", exc)	# 🐛 Логуємо причину відмови
        return None	# 🪣 Повертаємо значення за замовчуванням


def _normalize_image_url(src: str) -> str:
    """Уніфікує URL зображення для подальшої обробки."""
    if not src:	# 🚫 Немає посилання
        return ""	# 🪣 Повертаємо порожній рядок
    head = src.split(" ")[0]	# ✂️ Відсікаємо дані srcset
    if head.startswith("//"):	# 🌐 Вирівнюємо протокол відносного URL
        return f"https:{head}"	# 🔗 Повертаємо абсолютний URL
    return head	# 🔁 Використовуємо оброблений шлях


def _strip_query(u: str) -> str:
    """Прибирає query-параметри та фрагмент із URL."""
    if not u:	# 🚫 Немає адреси
        return ""	# 🪣 Порожній рядок
    return u.split("?", 1)[0]	# ✂️ Відкидаємо параметри запиту


def _clean_text_nodes(nodes: Iterable[Union[str, NavigableString, Tag, PageElement]]) -> str:
    """Об'єднує текстові вузли у єдиний нормалізований рядок."""
    parts: List[str] = []	# 🧱 Акумулюємо очищені фрагменти
    for node in nodes:	# 🔁 Перебираємо вузли контенту
        if isinstance(node, (str, NavigableString)):	# 🧵 Обробляємо текстові вузли
            text_fragment = _norm_ws(str(node))	# 🧹 Нормалізуємо фрагмент
            if text_fragment:	# ✅ Ігноруємо порожні рядки
                parts.append(text_fragment)	# 📥 Додаємо текст до списку
        elif isinstance(node, (Tag, PageElement)):	# 🧱 Працюємо з DOM-тегами
            try:	# 🧪 Пробуємо отримати текст із тегу
                extracted_text = cast(Tag, node).get_text(" ", strip=True)	# 🧾 Читаємо контент елемента
            except Exception:	# ⚠️ Виникли проблеми з get_text
                extracted_text = str(node)	# 🔁 Використовуємо сире представлення
            normalized = _norm_ws(extracted_text)	# 🧹 Нормалізуємо результат
            if normalized:	# ✅ Беремо лише непорожній текст
                parts.append(normalized)	# 📥 Акумулюємо очищений блок
    return _norm_ws(" ".join(parts))	# 🔗 Склеюємо фрагменти в один рядок

# ================================
# 🧱 СТРУКТУРА СЕЛЕКТОРІВ
# ================================
@dataclass(frozen=True)
class Selectors:
    """Структура із CSS-селекторами для екстракторів."""
    TITLE_LIST: Tuple[str, ...]
    PRICE_LIST: Tuple[str, ...]
    MAIN_IMAGE_LIST: Tuple[str, ...]
    ALL_IMAGES_LIST: Tuple[str, ...]
    DESCRIPTION_CONTAINER_LIST: Tuple[str, ...]
    JSON_LD_SCRIPT: str
    LEGACY_STOCK_SELECTORS: Tuple[str, ...]

# ================================
# 🧠 СНАПШОТ КОНФІГУРАЦІЇ
# ================================
class _ConfigSnapshot:
    """Керує кешами селекторів, фільтрів зображень і мап ключів."""
    _SELECTORS_CACHE: Optional[Dict[str, Any]] = None	# 🧠 Кеш параметрів селекторів
    _IMG_FILTERS_CACHE: Dict[str, Dict[str, Any]] = {}	# 🖼️ Кеш фільтрів зображень за брендом
    _KEY_MAP_BY_LOCALE: Dict[str, Dict[str, str]] = {}	# 🗺️ Кеш мап ключів за локаллю

    @classmethod
    def _as_tuple(cls, value: Any) -> Tuple[str, ...]:
        """Перетворює значення конфігу на кортеж рядків."""
        if value is None:	# 🚫 Значення відсутнє
            return tuple()	# 📦 Порожній кортеж
        if isinstance(value, (list, tuple)):	# 📚 У конфігу вже передано послідовність
            return tuple(str(x).strip() for x in value if str(x).strip())	# 🧹 Нормалізуємо кожен елемент
        normalized = str(value).strip()	# 🧹 Очищаємо одиночне значення
        return (normalized,) if normalized else tuple()	# 📦 Повертаємо кортеж із одного елемента

    @classmethod
    def _merge_selectors_dict(
        cls,
        defaults: Dict[str, Any],
        cfg_defaults: Dict[str, Any],
        brand_overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Об'єднує дефолтні селектори з конфігурацією та бренд-оверрайдами."""
        merged: Dict[str, Any] = dict(defaults)	# 🧱 Стартуємо з базових селекторів

        def _apply(src: Dict[str, Any]) -> None:
            for key, val in (src or {}).items():	# 🔁 Обходимо джерело оновлень
                if key in merged:	# ✅ Оновлюємо лише відомі ключі
                    merged[key] = val	# 🔄 Підміняємо селектор значенням конфігу

        if isinstance(cfg_defaults, dict):	# 🔍 Перевіряємо загальні налаштування
            _apply(cfg_defaults)	# 🔄 Застосовуємо дефолти конфігу
        if isinstance(brand_overrides, dict):	# 🏷️ Перевіряємо наявність бренд-оверрайдів
            _apply(brand_overrides)	# 🔄 Підміна селекторів бренду
        return merged	# 📦 Повертаємо змерджений словник

    @classmethod
    def _normalize_selectors_types(cls, sel: Dict[str, Any]) -> Dict[str, Any]:
        """Приводить значення селекторів до очікуваних типів."""
        normalized: Dict[str, Any] = dict(sel)	# 🧹 Створюємо копію словника
        normalized["TITLE_LIST"] = cls._as_tuple(normalized.get("TITLE_LIST"))	# 🏷️ Нормалізуємо заголовки
        normalized["PRICE_LIST"] = cls._as_tuple(normalized.get("PRICE_LIST"))	# 💰 Нормалізуємо селектори цін
        normalized["MAIN_IMAGE_LIST"] = cls._as_tuple(normalized.get("MAIN_IMAGE_LIST"))	# 🖼️ Основні зображення
        normalized["ALL_IMAGES_LIST"] = cls._as_tuple(normalized.get("ALL_IMAGES_LIST"))	# 🖼️ Усі зображення
        normalized["DESCRIPTION_CONTAINER_LIST"] = cls._as_tuple(
            normalized.get("DESCRIPTION_CONTAINER_LIST")
        )	# 📝 Секції опису
        normalized["LEGACY_STOCK_SELECTORS"] = cls._as_tuple(
            normalized.get("LEGACY_STOCK_SELECTORS")
        )	# 📦 Резервні селектори залишків
        json_script = normalized.get("JSON_LD_SCRIPT")	# 📄 Поточний селектор JSON-LD
        normalized["JSON_LD_SCRIPT"] = (
            str(json_script)
            if json_script not in (None, "")
            else _DEFAULT_SELECTORS["JSON_LD_SCRIPT"]
        )	# 🧾 Повертаємо валідний селектор JSON-LD
        return normalized	# 📦 Оновлений словник селекторів

    @classmethod
    def selectors(cls) -> Selectors:
        """Повертає dataclass із селекторами, використовуючи кешування."""
        if cls._SELECTORS_CACHE is None:	# 🧠 Ініціалізуємо кеш за потреби
            cfg = ConfigService()	# ⚙️ Отримуємо доступ до конфігу
            brand_candidate = (
                cfg.get("parser.selectors.brand")
                or cfg.get("brand")
                or cfg.get("brand.current")
                or cfg.get("parser.brand")
            )	# 🏷️ Зчитуємо бренд із конфігів
            brand = (str(brand_candidate).strip().lower() if isinstance(brand_candidate, str) else None) or None	# 🧹 Нормалізуємо бренд
            sel_defaults = cfg.get("parser.selectors.defaults") or {}	# 🧾 Глобальні селектори-перевизначення
            brand_overrides: Dict[str, Any] = {}	# 🧱 Порожній словник оверрайдів бренду
            if brand:	# ✅ Якщо бренд вказано
                brands_root = cfg.get("parser.selectors.brands") or {}	# 🗂️ Розділ брендів у конфігу
                if isinstance(brands_root, dict):	# 🔍 Переконуємося, що структура словникова
                    brand_overrides = brands_root.get(brand) or {}	# 🏷️ Беремо секцію конкретного бренду
            merged = cls._merge_selectors_dict(_DEFAULT_SELECTORS, sel_defaults, brand_overrides)	# 🔄 Об'єднуємо селектори
            cls._SELECTORS_CACHE = cls._normalize_selectors_types(merged)	# 🧠 Зберігаємо результат у кеші
            logger.debug("🔧 Селектори екстрактора завантажені (brand=%s).", brand or "default")	# 🐛 Діагностика ініціалізації
        selectors_cache = cls._SELECTORS_CACHE	# 📦 Беремо кешоване значення
        assert selectors_cache is not None	# 🛡️ Страхуємося від None
        return Selectors(	# 🧱 Створюємо dataclass селекторів
            TITLE_LIST=selectors_cache["TITLE_LIST"],	# 🏷️ Селектори заголовку
            PRICE_LIST=selectors_cache["PRICE_LIST"],	# 💰 Селектори цін
            MAIN_IMAGE_LIST=selectors_cache["MAIN_IMAGE_LIST"],	# 🖼️ Головне зображення
            ALL_IMAGES_LIST=selectors_cache["ALL_IMAGES_LIST"],	# 🖼️ Усі зображення
            DESCRIPTION_CONTAINER_LIST=selectors_cache["DESCRIPTION_CONTAINER_LIST"],	# 📝 Контейнери опису
            JSON_LD_SCRIPT=selectors_cache["JSON_LD_SCRIPT"],	# 📄 JSON-LD скрипти
            LEGACY_STOCK_SELECTORS=selectors_cache["LEGACY_STOCK_SELECTORS"],	# 📦 Резервні селектори наявності
        )

    @classmethod
    def img_filters(cls) -> Dict[str, Any]:
        """Повертає параметри фільтрації зображень із урахуванням бренду."""
        cfg = ConfigService()	# ⚙️ Читаємо конфіг
        brand_raw = (
            cfg.get("parser.selectors.brand")
            or cfg.get("brand")
            or cfg.get("brand.current")
            or cfg.get("parser.brand")
        )	# 🏷️ Бренд із конфігурацій
        brand: Optional[str] = (str(brand_raw).strip().lower() if isinstance(brand_raw, str) else None) or None	# 🧹 Нормалізуємо назву бренду
        cache_key = brand or "default"	# 🧠 Ключ кешу для бренду
        if cache_key in cls._IMG_FILTERS_CACHE:	# ✅ Якщо є у кеші
            return cls._IMG_FILTERS_CACHE[cache_key]	# 🔁 Повертаємо кешовані фільтри

        defaults = {
            "allowed_ext": [".jpg", ".jpeg", ".png", ".webp", ".avif"],
            "bad_tokens": [
                "sprite", "favicon", "logo", "icon", "spinner", "loading",
                "placeholder", "badge", "swatch", "thumb", "minicart", "lazy",
            ],
            "min_side_px": 120,
        }	# 🧱 Базові значення фільтрів

        global_allowed = cfg.get("parser.images.allowed_ext", defaults["allowed_ext"], cast=list) or defaults["allowed_ext"]	# 🌐 Глобально дозволені розширення
        global_bad = cfg.get("parser.images.bad_tokens", defaults["bad_tokens"], cast=list) or defaults["bad_tokens"]	# 🚫 Ключові слова, яких слід уникати
        global_minpx = cfg.get("parser.images.min_side_px", defaults["min_side_px"], cast=int) or defaults["min_side_px"]	# 📏 Мінімальний розмір зображення

        brand_allowed: Optional[List[Any]] = None	# 🖼️ Перелік дозволених розширень від бренду
        brand_bad: Optional[List[Any]] = None	# 🚫 Небажані токени з налаштувань бренду
        brand_minpx: Optional[int] = None	# 📏 Мінімальний розмір з конфігу бренду
        if brand:	# ✅ Маємо конкретний бренд
            brands_root = cfg.get("parser.selectors.brands") or {}	# 🗂️ Дерево налаштувань брендів
            if isinstance(brands_root, dict):	# 🔍 Перевіряємо структуру
                brand_node = brands_root.get(brand) or {}	# 🏷️ Налаштування бренду
                if isinstance(brand_node, dict):	# 🔍 Валідність структури
                    images_node = brand_node.get("images")	# 🖼️ Секція зображень
                    if isinstance(images_node, dict):	# 🔍 Переконуємося у валідності
                        brand_allowed = images_node.get("allowed_ext")	# 🖼️ Перевизначені дозволені розширення
                        brand_bad = images_node.get("bad_tokens")	# 🚫 Специфічні небажані токени
                        brand_minpx = images_node.get("min_side_px")	# 📏 Мінімальний розмір для бренду

        allowed_ext = brand_allowed if isinstance(brand_allowed, list) else global_allowed	# 🧾 Обираємо джерело дозволених розширень
        bad_tokens = brand_bad if isinstance(brand_bad, list) else global_bad	# 🚫 Формуємо список небажаних токенів
        min_side_px = brand_minpx if isinstance(brand_minpx, int) else global_minpx	# 📏 Фіксуємо мінімальний розмір

        allowed_ext = [str(x).lower().strip() for x in allowed_ext if str(x).strip()]	# 🧹 Нормалізуємо розширення
        bad_tokens = [str(x).lower().strip() for x in bad_tokens if str(x).strip()]	# 🧹 Нормалізуємо токени
        try:	# 🧪 Перевіряємо мінімальний розмір
            min_side_px = int(min_side_px)	# 🔁 Конвертуємо у число
        except Exception:	# ⚠️ У fallback віддаємо дефолт
            min_side_px = defaults["min_side_px"]	# 📏 Використовуємо базовий поріг

        filters = {
            "allowed_ext": tuple(allowed_ext),
            "bad_tokens": tuple(bad_tokens),
            "min_side_px": min_side_px,
        }	# 🧱 Формуємо результат для повернення
        cls._IMG_FILTERS_CACHE[cache_key] = filters	# 🧠 Кешуємо значення для бренду
        return filters	# 📦 Повертаємо фільтри

    @classmethod
    def key_map_for_locale(cls, locale: str) -> Dict[str, str]:
        """Повертає мапу ключів характеристик для заданої локалі."""
        loc = (locale or "uk").strip().lower()	# 🧹 Нормалізуємо назву локалі
        if loc == "ua":	# 🔄 Узгоджуємо позначення UA → UK
            loc = "uk"	# 🏷️ Встановлюємо фінальну локаль
        if loc not in cls._KEY_MAP_BY_LOCALE:	# 🧠 Перевіряємо кеш
            cls._KEY_MAP_BY_LOCALE[loc] = cls._load_key_map_from_locale(loc)	# ♻️ Завантажуємо та кешуємо мапу
        return cls._KEY_MAP_BY_LOCALE[loc]	# 📦 Повертаємо результат

    @classmethod
    def _load_key_map_from_locale(cls, locale: str) -> Dict[str, str]:
        """Завантажує мапу ключів із ресурсів i18n."""

        def _read(locale_code: str) -> Optional[Dict[str, str]]:
            """Читає YAML-файл локалі та повертає key_map."""
            try:	# 🧪 Прагнемо відкрити ресурс локалізації
                with pkg_resources.files("app.i18n").joinpath(f"{locale_code}.yml").open("r", encoding="utf-8") as handle:	# 📂 Відкриваємо файл локалізації
                    data = yaml.safe_load(handle) or {}	# 📄 Завантажуємо YAML як словник
                key_map = data.get("key_map") if isinstance(data, dict) else None	# 🗺️ Вибираємо секцію `key_map`
                if isinstance(key_map, dict):	# ✅ Переконуємося у валідності типу
                    normalized = {	# 🧹 Формуємо нормалізовану мапу
                        str(key).upper(): str(value)
                        for key, value in key_map.items()
                        if str(key).strip()
                    }
                    if normalized:	# ✅ Маємо наповнений словник
                        return normalized	# 📦 Повертаємо мапу
            except Exception as exc:	# ⚠️ Не вдалося прочитати ресурс
                logger.debug("🐛 Неможливо завантажити key_map для локалі %s: %s", locale_code, exc)	# 🐛 Діагностика проблеми
                return None	# 🪣 Повертаємо None як сигнал
            return None	# 🪣 Даних не знайдено

        for candidate in (locale, "en"):	# 🔁 Шукаємо локаль та резерв англійську
            mapping = _read(candidate)	# 📥 Пробуємо завантажити мапу
            if mapping:	# ✅ Якщо мапу знайдено
                return mapping	# 📦 Повертаємо результат
        return dict(_FALLBACK_KEY_MAP)	# 🔁 Віддаємо дефолтний fallback

# ================================
# 📤 ЕКСПОРТ МОДУЛЯ
# ================================
__all__ = [
    "Selectors",	# 🧱 Dataclass селекторів
    "_ConfigSnapshot",	# 🧠 Кешуючий snapshot конфігурації
    "_norm_ws",	# 🧹 Нормалізація пробілів
    "_attr_to_str",	# 🧾 Перетворення атрибутів у рядок
    "_as_list",	# 📦 Обгортання у список
    "_try_json_loads",	# 📄 Безпечне читання JSON
    "_normalize_image_url",	# 🖼️ Нормалізація URL зображень
    "_strip_query",	# ✂️ Прибирання query з URL
    "_clean_text_nodes",	# 🧹 Очищення текстових вузлів
    "uniq_keep_order",	# ♻️ Дедуплікація списків із збереженням порядку
    "BeautifulSoup",	# 🥣 Re-export для сумісності
    "Tag",	# 🧱 Тип DOM-тегу
    "PageElement",	# 🧱 Абстракція елементу DOM
    "NavigableString",	# 🧵 Текстовий вузол BeautifulSoup
    "logger",	# 🧾 Експортований логер
]
