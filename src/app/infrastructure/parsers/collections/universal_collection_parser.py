# 📚 app/infrastructure/parsers/collections/universal_collection_parser.py
"""
📚 `UniversalCollectionParser` — INFRA-рівень для парсингу колекцій YoungLA.

🔹 Використовує єдиний HTML-парсер (конфігурується через фабрику).  
🔹 Спершу пробує JSON-LD, далі переходить до DOM + пагінації.  
🔹 Нормалізує URL (видаляє query/fragment, добудовує абсолютні посилання).  
🔹 Повертає список унікальних посилань на товари.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup												# 🥣 Розбір HTML

# 🔠 Системні імпорти
import json																# 🧾 Робота з JSON-LD
import logging															# 🧾 Логування подій
import re																# 🧮 Перевірка/маніпуляція рядків
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple		# 🧰 Узгоджена типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService					# ⚙️ Конфігурація INFRA
from app.infrastructure.web.webdriver_service import WebDriverService	# 🌐 Завантаження сторінок
from app.shared.utils.url_parser_service import UrlParserService		# 🌍 Нормалізація URL

logger = logging.getLogger(__name__)									# 🧾 Модульний логер


# ================================
# 🔧 УТИЛІТИ (СТРОГО-ТИПОБЕЗПЕЧНІ)
# ================================
def _safe_json_loads(raw: Optional[str]) -> Optional[Any]:
    """📄 Безпечний json.loads із захистом від винятків."""

    if not raw:
        return None														# 💤 Немає даних — повертаємо None
    try:
        return json.loads(raw)											# ✅ Спроба розпарсити JSON
    except Exception:
        return None														# 🚫 Некоректний JSON


def _uniq_keep_order(seq: Iterable[str]) -> List[str]:
    """🔁 Повертає унікальні значення, зберігаючи порядок."""

    out: List[str] = []													# 📦 Результат
    seen: Set[str] = set()												# 👁️‍🗨️ Відстежуємо зустрінуті значення
    for value in seq:
        if not value or value in seen:
            continue													# ⏭️ Пропускаємо пусті/дублі
        seen.add(value)													# 🔖 Позначаємо як опрацьоване
        out.append(value)												# ➕ Додаємо до результату
    return out


def _strip_query_and_fragment(url: str) -> str:
    """✂️ Видаляє query/fragment з URL."""

    if not url:
        return ""
    base = url.split("#", 1)[0]											# 🧵 Прибираємо fragment
    base = base.split("?", 1)[0]											# 🧵 Прибираємо query
    return base


def _is_product_like_path(href: str) -> bool:
    """🔍 Перевіряє, чи містить шлях `/products/`."""

    return "/products/" in (href or "").lower()


def _ensure_abs(base_url: str, href: str) -> str:
    """🌐 Будує абсолютний URL за базовим доменом."""

    if not href:
        return ""
    cleaned = href.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("//"):
        return "https:" + cleaned										# 🌐 Протокол-залежний URL
    if cleaned.startswith("/"):
        return base_url.rstrip("/") + cleaned							# 🏠 Відносний шлях
    if not cleaned.startswith("http"):
        return base_url.rstrip("/") + "/" + cleaned.lstrip("/")		# 🧵 Інший відносний шлях
    return cleaned														# ✅ Вже абсолютний


def _maybe_normalize(url_parser_service: UrlParserService, url: str) -> str:
    """🧼 Викликає normalize, якщо сервіс його підтримує."""

    try:
        normalize = getattr(url_parser_service, "normalize", None)		# 🧠 Шукаємо метод
        if callable(normalize):
            result = normalize(url)										# type: ignore[no-any-return]
            return str(result or "").strip()							# 🧽 Повертаємо очищений URL
    except Exception:
        pass															# 🤫 Логіку normalize не нав'язуємо
    return url															# 🔁 Без змін


def _get_attr_str(tag: Any, attr: str) -> str:
    """🏷️ Дістає атрибут тега як рядок."""

    if tag is None:
        return ""
    try:
        value = tag.get(attr)  # type: ignore[attr-defined]
    except Exception:
        return ""													# 🚫 Метод get недоступний
    if isinstance(value, list):										# 🧺 BeautifulSoup може повертати list
        for item in value:
            if isinstance(item, str) and item:
                return item
        return ""
    return value if isinstance(value, str) else ""					# ✅ Рядок або пусто


def _get_script_text(script: Any) -> str:
    """📜 Повертає текст скрипта (`string` або `text`)."""

    if script is None:
        return ""
    try:
        direct = getattr(script, "string", None)						# 🧵 string — більш точний
        if isinstance(direct, str) and direct:
            return direct
        fallback = getattr(script, "text", "")
        return fallback if isinstance(fallback, str) else ""
    except Exception:
        return ""


# ================================
# 🏛️ ПАРСЕР КОЛЕКЦІЇ
# ================================
class UniversalCollectionParser:
    """
    🏛️ Витягує всі посилання на товари з колекцій YoungLA.

    Кроки:
      1. Завантажити сторінку через `WebDriverService`.
      2. Спробувати знайти продукти в JSON-LD.
      3. Якщо JSON-LD порожній — fallback на DOM із пагінацією.
      4. Нормалізувати URL та повернути унікальний список.
    """

    MIN_PAGE_LENGTH_BYTES = 1200											# 📏 Мінімальний розмір сторінки

    PRODUCT_LINK_SELECTORS: Tuple[str, ...] = (							# 🎯 Селектори продуктів
        'a[href*="/products/"]',
        '[data-product-url*="/products/"]',
        '.product-card a[href*="/products/"]',
        '.grid-product a[href*="/products/"]',
        '.card a[href*="/products/"]',
        '.product-tile a[href*="/products/"]',
        '.product-item a[href*="/products/"]',
        '.collection-product-card a[href*="/products/"]',
        '.product-grid a[href*="/products/"]',
    )

    NEXT_SELECTORS: Tuple[str, ...] = (									# 🔁 Селектори пагінації
        'link[rel="next"]',
        'a[rel="next"]',
        'a.pagination__next',
        'a[aria-label="Next"]',
        'a[title="Next"]',
        '.pagination a.next',
        '.pagination__item--next',
    )

    MAX_PAGINATION_PAGES = 5												# 🚦 Обмеження переходів

    def __init__(
        self,
        url: str,
        webdriver_service: WebDriverService,
        config_service: ConfigService,
        url_parser_service: UrlParserService,
        *,
        html_parser: str = "lxml",
    ) -> None:
        self.url = url													# 🌐 Поточний URL колекції
        self.webdriver_service = webdriver_service						# 🌍 Сервіс завантаження сторінок
        self.config_service = config_service							# ⚙️ Конфіг INFRA
        self.url_parser_service = url_parser_service					# 🌍 Нормалізація/валюта
        self.html_parser = html_parser									# 🧵 Обраний HTML-парсер
        self.soup: Optional[BeautifulSoup] = None						# 🥣 Parsed DOM
        self.page_source: Optional[str] = None							# 🧾 HTML сторінки
        self.currency: Optional[str] = self.url_parser_service.get_currency(self.url)  # 💱 Поточна валюта

    # ================================
    # 🔗 ПУБЛІЧНИЙ МЕТОД
    # ================================
    async def get_product_links(self) -> List[str]:
        """🔗 Повертає унікальний список посилань на товари."""

        if not await self._fetch_page(self.url):							# 🌐 Спочатку завантажуємо першу сторінку
            logger.warning("❌ Колекція не завантажена: %s", self.url)
            return []

        json_ld_links = self._parse_from_json_ld(self.soup)				# 📄 Спроба через JSON-LD
        if json_ld_links:
            logger.info("✅ JSON-LD дав %d посилань (без пагінації).", len(json_ld_links))
            return json_ld_links

        accumulated = self._parse_from_dom(self.soup)						# 🌐 DOM-fallback

        base_url = self._base_url()										# 🏠 Базовий домен
        next_url = self._find_next_url(self.soup, base_url)				# 🔁 Пошук наступної сторінки
        hops = 0															# 🔢 Лічильник сторінок
        while next_url and hops < self.MAX_PAGINATION_PAGES:				# ⏱️ Обмежуємо пагінацію
            hops += 1
            if not await self._fetch_page(next_url):						# 🌐 Пробуємо завантажити наступну сторінку
                break
            accumulated.extend(self._parse_from_dom(self.soup))			# ➕ Додаємо нові лінки
            next_url = self._find_next_url(self.soup, base_url)			# 🔁 Переходимо далі

        unique_links = _uniq_keep_order(accumulated)						# 🔁 Прибираємо дублі
        logger.info("📦 DOM-режим: зібрано %d посилань (включно з пагінацією).", len(unique_links))
        return unique_links

    # ================================
    # 🕵️‍♂️ ЗАВАНТАЖЕННЯ СТОРІНКИ
    # ================================
    async def _fetch_page(self, url: str) -> bool:
        """🌐 Завантажує сторінку та готує `BeautifulSoup`."""

        try:
            html = await self.webdriver_service.get_page_content(			# 🌐 Отримуємо HTML
                url,
                wait_until="networkidle",
                timeout_ms=30000,
                retries=1,
                retry_delay_sec=1,
                use_stealth=True,
            )
        except Exception as exc:
            logger.error("❌ Помилка під час завантаження %s: %s", url, exc)
            self.page_source = None										# 🧹 Очищаємо сторінку
            self.soup = None												# 🧹 Очищаємо парсер
            return False

        self.page_source = html											# 🧾 Кешуємо сирий HTML
        if html and len(html) > self.MIN_PAGE_LENGTH_BYTES:				# 📏 Перевіряємо на мінімальний розмір
            self.soup = BeautifulSoup(html, self.html_parser)				# 🥣 Створюємо парсер
            logger.info("✅ Сторінка колекції завантажена: %s", url)
            self.url = url												# 🔄 Оновлюємо поточний URL
            return True

        logger.error("❌ Не вдалося завантажити сторінку або вона занадто коротка: %s", url)
        self.soup = None
        return False

    # ================================
    # 📄 JSON-LD
    # ================================
    def _parse_from_json_ld(self, soup: Optional[BeautifulSoup]) -> List[str]:
        """📄 Витягує посилання з блоків JSON-LD."""

        if not soup:
            return []

        base_url = self._base_url()
        found: List[str] = []

        for script in soup.find_all("script", type="application/ld+json"):
            raw_obj = _safe_json_loads(_get_script_text(script))			# 🧾 Розпарсимо JSON-LD
            if raw_obj is None:
                continue
            blocks = raw_obj if isinstance(raw_obj, list) else [raw_obj]	# 📦 Уніфікуємо список блоків
            for block in blocks:
                if not isinstance(block, dict):
                    continue

                atype = block.get("@type")
                types = {str(atype).lower()} if not isinstance(atype, list) else {str(item).lower() for item in atype}
                if not {"collectionpage", "searchresultspage", "itemlist"} & types:
                    continue												# ❌ Блок не схожий на колекцію

                links = self._links_from_ld_collection(block)				# 🔍 Витягуємо посилання з itemList
                if not links:
                    continue

                for raw_href in links:
                    abs_url = _ensure_abs(base_url, raw_href)				# 🌐 Добудовуємо абсолютний URL
                    abs_url = _strip_query_and_fragment(abs_url)			# 🧼 Очищаємо від query/fragment
                    if _is_product_like_path(abs_url):
                        found.append(_maybe_normalize(self.url_parser_service, abs_url))

        return _uniq_keep_order(found)

    def _links_from_ld_collection(self, block: Dict[str, Any]) -> List[str]:
        """📦 Допоміжний метод: витягує href із JSON-LD."""

        def _extract_href(node: Any) -> Optional[str]:
            if not node:
                return None
            if isinstance(node, str):
                return node												# 🧾 Прямий URL
            if isinstance(node, dict):
                href = node.get("url") or node.get("@id") or node.get("identifier")
                if isinstance(href, str) and href:
                    return href											# 📎 Початкові поля з URL
                node_type = node.get("@type")
                if isinstance(node_type, str) and node_type.lower() in {"listitem", "list_item"}:
                    return _extract_href(node.get("item"))				# 🔄 Рекурсія всередину item
                if "item" in node:
                    return _extract_href(node.get("item"))
            return None													# ❌ Нічого не знайшли

        items: Any = None
        main_entity = block.get("mainEntity")
        if isinstance(main_entity, dict):
            items = main_entity.get("itemListElement")					# 🔄 Часто mainEntity містить itemListElement
        if items is None:
            items = block.get("itemListElement")							# 🔁 Фолбек на верхній рівень

        if items is None:
            return []
        if not isinstance(items, list):
            items = [items]												# 🧾 Уніфікуємо до списку

        out: List[str] = []
        for element in items:
            href = _extract_href(element)
            if isinstance(href, str) and href:
                out.append(href)
        return out

    # ================================
    # 🌐 DOM-FALLBACK
    # ================================
    def _parse_from_dom(self, soup: Optional[BeautifulSoup]) -> List[str]:
        """🌐 Витягує посилання з DOM, якщо JSON-LD порожній."""

        if not soup:
            return []

        base_url = self._base_url()
        acc: List[str] = []

        for selector in self.PRODUCT_LINK_SELECTORS:
            try:
                for element in soup.select(selector):
                    href = (_get_attr_str(element, "href") or _get_attr_str(element, "data-product-url")).strip()
                    if not href:
                        continue
                    href = _ensure_abs(base_url, href)					# 🌐 Абсолютний URL
                    href = _strip_query_and_fragment(href)				# ✂️ Очищаємо
                    if _is_product_like_path(href):
                        acc.append(_maybe_normalize(self.url_parser_service, href))
            except Exception as exc:
                logger.warning("DOM selector failed '%s': %s", selector, exc)

        return _uniq_keep_order(acc)

    # ================================
    # 👉 ПАГІНАЦІЯ
    # ================================
    def _find_next_url(self, soup: Optional[BeautifulSoup], base_url: str) -> Optional[str]:
        """👉 Шукає посилання на наступну сторінку."""

        if not soup:
            return None

        tag = soup.select_one('link[rel="next"]')							# 🔗 Якнайпростіший випадок
        href = _get_attr_str(tag, "href")
        if href:
            href = _ensure_abs(base_url, href)
            return _strip_query_and_fragment(href)

        for selector in self.NEXT_SELECTORS:								# 🔁 Пробуємо кілька селекторів
            anchor = soup.select_one(selector)
            href = _get_attr_str(anchor, "href")
            if href:
                href = _ensure_abs(base_url, href)
                return _strip_query_and_fragment(href)

        try:
            pagination = soup.select_one(".pagination")
            if pagination:
                active = pagination.select_one(".active")
                if active:
                    next_anchor = active.find_next("a")
                    href = _get_attr_str(next_anchor, "href")
                    if href:
                        href = _ensure_abs(base_url, href)
                        return _strip_query_and_fragment(href)
        except Exception:
            pass															# 🤫 Пагінація не критична

        return None

    # ================================
    # 🔗 БАЗА РЕГІОНУ/ДОМЕНУ
    # ================================
    def _base_url(self) -> str:
        """🌍 Повертає базовий домен для побудови абсолютних URL."""

        currency = (self.currency or "USD").upper()						# 💱 Валюта сторінки
        try:
            base = self.url_parser_service.get_base_url(currency)			# 🌍 Перетворюємо валюту в базовий домен
            if isinstance(base, str) and base:
                return base
        except Exception as exc:
            logger.warning("url_parser_service.get_base_url failure: %s", exc)
        return "https://www.youngla.com"									# 🏠 Фолбек: глобальний домен
