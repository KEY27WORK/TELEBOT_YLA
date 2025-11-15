# 🧾 app/infrastructure/parsers/extractors/json_ld.py
"""
🧾 JsonLdMixin — утиліти для витягування даних товару з JSON-LD блоків.

🔹 Збирає усі JSON-LD скрипти сторінки та фільтрує лише обʼєкти `Product`.
🔹 Повертає назву, опис, ціну, основні/додаткові зображення та наявність.
🔹 Використовується разом із `ImagesMixin`/`DescriptionMixin` у базових парсерах.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import re	# 🧪 Патерни для розбору SKU/розмірів
from typing import Any, Dict, List, Optional, Tuple, cast	# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from .base import (	# 🔗 Спільні утиліти екстракторів
    BeautifulSoup,
    Selectors,
    Tag,
    _ConfigSnapshot,
    _as_list,
    _norm_ws,
    _normalize_image_url,
    _strip_query,
    _try_json_loads,
    logger,
)


class JsonLdMixin:
    """📦 Надає методи для парсингу даних продукту з JSON-LD."""

    _S: Selectors	# 🧷 Кешовані селектори
    soup: BeautifulSoup	# 🥣 DOM-дерево (інʼєктується BaseParser)

    # ================================
    # 📄 БЛОКИ JSON-LD
    # ================================
    def _json_ld_blocks(self) -> List[Any]:
        """📄 Збирає всі JSON-LD скрипти, повертає у вигляді списку обʼєктів."""
        blocks: List[Any] = []	# 📦 Контейнер для JSON-LD
        for script in self.soup.select(self._S.JSON_LD_SCRIPT):	# 🔍 Проходимо по всіх <script type="application/ld+json">
            if not isinstance(script, Tag):	# 🚫 Не тег → пропускаємо
                continue
            raw = (script.string or script.text or "").strip()	# 🧼 Чистимо вміст
            obj = _try_json_loads(raw)	# 🧮 Парсимо JSON
            if obj is None:	# 🚫 Некоректний JSON
                continue
            blocks.extend(_as_list(obj))	# ♻️ Навіть якщо це одиничний блок
        logger.debug("📄 JSON-LD: знайдено %d блоків.", len(blocks))	# 🪵 Діагностика
        return blocks

    def _json_ld_products(self) -> List[Dict[str, Any]]:
        """📦 Фільтрує лише обʼєкти продуктів (де @type містить Product)."""
        products: List[Dict[str, Any]] = []	# 📦 Результат
        for obj in self._json_ld_blocks():	# 🔁 Всі блоки JSON-LD
            if not isinstance(obj, dict):	# 🚫 Очікуємо dict
                continue
            types = _as_list(obj.get("@type"))	# 🧾 Може бути рядок/список
            if any(str(t).lower() == "product" for t in types):	# ✅ Product-блок
                products.append(obj)
        logger.debug("📦 JSON-LD: знайдено %d product-обʼєктів.", len(products))	# 🪵 Метрика
        return products

    # ================================
    # 🏷️ ПОЛЯ ПРОДУКТУ
    # ================================
    def _title_from_json_ld(self) -> Optional[str]:
        """🏷️ Повертає назву товару з JSON-LD."""
        for product in self._json_ld_products():	# 🔁 Обходимо продукти
            name = _norm_ws(str(product.get("name", "")))	# 🧼 Беремо поле name
            if name:	# ✅ Маємо значення
                logger.debug("🏷️ JSON-LD title знайдено: %s", name)	# 🪵 Підтвердження
                return name
        return None	# 🪣 Назву не знайдено

    def _description_from_json_ld(self) -> Optional[str]:
        """📝 Повертає опис товару із JSON-LD (рядок або @value)."""
        for idx, product in enumerate(self._json_ld_products(), start=1):	# 🔁 Пройдемось по продуктах
            description = product.get("description")	# 🧾 Поле description
            if isinstance(description, str):	# ✅ Рядок
                cleaned = _norm_ws(BeautifulSoup(description, "lxml").get_text(" ", strip=True))	# 🧼 Чистимо HTML
                if cleaned:
                    logger.debug("📝 JSON-LD description #%d (string) знайдено.", idx)
                    return cleaned
            if isinstance(description, dict):	# ✅ Обʼєкт з @value
                value = description.get("@value") or description.get("value") or description.get("text")	# 🔑 Можливі ключі
                if isinstance(value, str):
                    cleaned = _norm_ws(BeautifulSoup(value, "lxml").get_text(" ", strip=True))	# 🧼 Чистимо
                    if cleaned:
                        logger.debug("📝 JSON-LD description #%d (dict) знайдено.", idx)
                        return cleaned
        logger.info("📝 JSON-LD опис не знайдено.")
        return None	# 🪣 Опис відсутній

    def _price_from_json_ld(self) -> Optional[str]:
        """💰 Витягує ціну з offers/aggregateOffer."""
        for product in self._json_ld_products():	# 🔁 Кожен продукт
            offers_obj = product.get("offers")	# 💸 Блок offers
            if not offers_obj:	# 🚫 Немає пропозицій
                continue
            offers_list = self._extract_offers(offers_obj)	# 📦 Приводимо до списку
            for offer in offers_list:	# 🔁 Перебираємо пропозиції
                if not isinstance(offer, dict):	# 🚫 Очікуємо dict
                    continue
                price = self._first_not_empty(	# 💰 Визначаємо ціну
                    offer.get("price"),
                    self._price_from_spec(offer.get("priceSpecification")),
                    offer.get("lowPrice"),
                    offer.get("highPrice"),
                )
                if price not in (None, ""):	# ✅ Знайдено значення
                    return str(price)
        return None	# 🪣 Ціни немає

    def _main_image_from_json_ld(self) -> Optional[str]:
        """🖼️ Повертає головне зображення з JSON-LD (перший валідний URL)."""
        for product in self._json_ld_products():	# 🔁 Кожен продукт
            image_field = product.get("image")	# 🖼️ Поле image (str/list/dict)
            if not image_field:	# 🚫 Поле відсутнє
                continue
            for item in _as_list(image_field):	# 🔁 Проходимо значення
                url = self._normalize_image_item(item)	# 🧼 Нормалізуємо
                if url:	# ✅ Маємо посилання
                    logger.debug("🖼️ JSON-LD main image знайдено: %s", url)
                    return url
        logger.info("🖼️ Головне зображення у JSON-LD не знайдено.")
        return None	# 🪣 Зображення нема

    def _images_from_json_ld(self) -> List[str]:
        """🖼️ Повертає всі зображення з JSON-LD, зберігаючи порядок."""
        images: List[str] = []	# 📦 Акумулятор URL
        for product in self._json_ld_products():	# 🔁 Обходимо продукти
            image_field = product.get("image")	# 🖼️ Поле зображень
            if not image_field:	# 🚫 Поле пусте
                continue
            for item in _as_list(image_field):	# 🔁 Кожне значення
                url = self._normalize_image_item(item)	# 🧼 Нормалізація
                if url:
                    images.append(url)	# 📥 Додаємо у список
        logger.debug("🖼️ JSON-LD images: знайдено %d URL.", len(images))	# 🪵 Статистика
        return images

    # ================================
    # 📦 Наявність із offers
    # ================================
    def _offers_to_stock_map(self, offers_obj: Any) -> Dict[str, Dict[str, bool]]:
        """📦 Перетворює offers/aggregateOffer на карту наявності (color → size → bool)."""
        offers_list = self._extract_offers(offers_obj)	# ♻️ Нормалізуємо offers до списку
        stock: Dict[str, Dict[str, bool]] = {}	# 📦 Фінальний словник

        def _split_name(name: str) -> Tuple[Optional[str], Optional[str]]:
            """🔧 Повертає (color, size) з рядка назви/sku."""
            normalized = _norm_ws(name)	# 🧼 Чистимо пробіли
            if not normalized:	# 🪣 Порожнє значення
                return None, None
            for sep in (" / ", " - ", " | "):
                if sep in normalized:
                    a, b = normalized.split(sep, 1)	# 🔀 Розділяємо
                    return (a or "").strip() or None, (b or "").strip() or None
            match = re.match(r"^(?P<color>[A-Za-z].*?)\s+(?P<size>(?:\d+|[XSML]{1,4}\+?|\w{1,4}))$", normalized)	# 🔎 color size
            if match:	# ✅ Вдалий парсинг
                return match.group("color").strip(), match.group("size").strip()
            return None, None	# 🪣 Не вдалося

        for offer in offers_list:	# 🔁 Перебираємо всі пропозиції
            if not isinstance(offer, dict):
                continue
            availability = str(offer.get("availability", "")).lower()	# 🔍 Ознака наявності
            in_stock = "instock" in availability	# ✅ true/false
            name_field = str(offer.get("name") or "")	# 🏷️ Назва варіанта
            color_from_name, size_from_name = _split_name(name_field)	# 🎨/📏 З назви
            color = (color_from_name or offer.get("color") or offer.get("itemColor") or "").strip()	# 🎨 Колір
            size = (size_from_name or offer.get("size") or offer.get("itemSize") or "").strip()	# 📏 Розмір
            if (not color or not size) and isinstance(offer.get("sku"), str):	# 🔁 Fallback на SKU
                sku_color, sku_size = _split_name(cast(str, offer["sku"]))
                color = color or (sku_color or "")
                size = size or (sku_size or "")
            color = color or "DEFAULT"	# 🧾 Безпечні дефолти
            size = size or "DEFAULT"
            stock.setdefault(color, {})[size] = in_stock	# 📦 Зберігаємо прапорець
        logger.debug("📦 JSON-LD stock map: %d кольорів.", len(stock))	# 🪵 Статистика
        return stock

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _extract_offers(self, offers_obj: Any) -> List[Any]:
        """🧰 Приводить offers/aggregateOffer до списку пропозицій."""
        if isinstance(offers_obj, dict) and str(offers_obj.get("@type", "")).lower() == "aggregateoffer":	# 🔀 aggregateOffer
            raw_offers = offers_obj.get("offers") or []	# 📦 Поле offers
        else:
            raw_offers = offers_obj	# 📦 Може бути dict/list
        offers_list = _as_list(raw_offers)	# ♻️ Гарантуємо список
        logger.debug("🧰 offers normalized до %d елементів.", len(offers_list))	# 🪵 Діагностика
        return offers_list

    def _price_from_spec(self, spec_obj: Any) -> Optional[str]:
        """💰 Витягує price з priceSpecification (якщо це dict)."""
        if isinstance(spec_obj, dict):
            price = spec_obj.get("price")	# 🔍 Беремо поле price
            if price not in (None, ""):
                return str(price)
        return None

    @staticmethod
    def _first_not_empty(*values: Any) -> Optional[Any]:
        """🔁 Повертає перше непорожнє значення з перелічених."""
        for value in values:	# 🔁 Проходимо список
            if value not in (None, ""):
                return value
        return None

    def _normalize_image_item(self, item: Any) -> str:
        """🧼 Приводить поле image (str/dict) до очищеного URL."""
        if isinstance(item, str):	# ✅ Рядок
            url = _normalize_image_url(item)
        elif isinstance(item, dict):	# ✅ Обʼєкт
            url = _normalize_image_url(str(item.get("url") or item.get("@id") or ""))
        else:	# 🚫 Невідомий формат
            url = ""
        cleaned = _strip_query(url)	# 🧼 Прибираємо query
        return cleaned or ""
