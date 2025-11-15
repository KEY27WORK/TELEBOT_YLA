# 🧾 app/infrastructure/parsers/html_data_extractor.py
"""
🧾 HtmlDataExtractor — композиція JSON-LD, зображень та описів для сторінки товару.

🔹 Забезпечує єдиний API витягування (title/price/description/images/stock).
🔹 Перемикає джерела даних між JSON-LD, метаданими та DOM-селекторами.
🔹 Пропонує діагностику завдяки детальному логуванню на кожному кроці.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup	# 🥣 DOM-дерево сторінки
from bs4.element import Tag	# 🧱 Тип елементів BeautifulSoup

# 🔠 Системні імпорти
import logging	# 🧾 Логування сценаріїв
import re	# 🧪 Пошук числових патернів
from typing import Any, Dict, List, Optional, Tuple, Union, cast	# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME	# 🏷️ Імʼя базового логера
from .extractors.base import _ConfigSnapshot, Selectors, _norm_ws, _try_json_loads	# 🧱 Спільні утиліти
from .extractors.description import DescriptionMixin	# 📜 Побудова описів
from .extractors.images import ImagesMixin	# 🖼️ Витяг зображень
from .extractors.json_ld import JsonLdMixin	# 📄 Робота з JSON-LD

# ================================
# 🧾 ЛОГЕР ТА КОНСТАНТИ
# ================================
logger = logging.getLogger(f"{LOG_NAME}.parser.extractor")	# 🧾 Модульний логер
_TITLE_FALLBACK = "Без назви"	# 🏷️ Стандартна назва за відсутності заголовка


# ================================
# 🏛️ ОСНОВНИЙ ЕКСТРАКТОР
# ================================
class HtmlDataExtractor(JsonLdMixin, ImagesMixin, DescriptionMixin):
    """🏛️ Оркеструє роботу mixin-класів для витягування даних товару."""

    def __init__(self, soup: BeautifulSoup, *, locale: Optional[str] = None) -> None:
        """⚙️ Зберігає `BeautifulSoup` та кешує селектори/мапи ключів."""
        self.soup = soup	# 🥣 DOM-дерево для подальшого використання
        self._S: Selectors = _ConfigSnapshot.selectors()	# 🧱 Кешовані селектори з конфігу
        locale_code = locale or "uk"	# 🗺️ Локаль за замовчуванням
        self._KEY_MAP = _ConfigSnapshot.key_map_for_locale(locale_code)	# 🗺️ Відповідність ключів секцій
        logger.debug("🧾 HtmlDataExtractor ініціалізовано (locale=%s).", locale_code)	# 🪵 Фіксуємо контекст

    # ================================
    # 🏷️ ЗАГОЛОВОК / ЦІНА
    # ================================
    def extract_title(self) -> str:
        """🏷️ Повертає назву товару з JSON-LD, meta або DOM."""
        json_title = self._title_from_json_ld()	# 📄 Перший кандидат — JSON-LD
        if json_title:	# ✅ Якщо JSON-LD містив заголовок
            logger.debug("🏷️ Заголовок знайдено у JSON-LD: %s", json_title)	# 🪵 Фіксуємо джерело
            return json_title	# 🔁 Повертаємо результат

        for selector in self._S.TITLE_LIST:	# 🔁 Перебираємо селектори з конфігу
            tag = self.soup.select_one(selector)	# 🔍 Пробуємо знайти елемент
            if not tag:	# ⛔️ Нічого не знайшли
                continue	# 🔁 Переходимо до наступного селектора
            if isinstance(tag, Tag) and tag.name == "meta":	# 🏷️ Meta-тег потребує content
                text = str(tag.get("content") or "")	# 🧾 Отримуємо значення content
            else:	# 📄 Інші теги
                try:
                    text = cast(Tag, tag).get_text(strip=True)	# 🧾 Збираємо текст без пробілів
                except Exception:	# ⚠️ Помилка отримання тексту
                    text = str(tag)	# 🔁 Використовуємо сире представлення
            normalized = _norm_ws(text)	# 🧼 Нормалізуємо пробіли
            if normalized:	# ✅ Маємо контент
                logger.debug("🏷️ Заголовок знайдено селектором '%s'.", selector)	# 🪵 Джерело даних
                return normalized	# 🔁 Повертаємо заголовок
        logger.warning("⚠️ Заголовок не знайдено — повертаємо fallback.")	# ⚠️ Попереджаємо про дефолт
        return _TITLE_FALLBACK	# 🏷️ Повертаємо стандартне значення

    def extract_price(self) -> Union[str, float]:
        """💰 Повертає ціну як рядок або float (fallback)."""
        json_price = self._price_from_json_ld()	# 💾 Перевіряємо JSON-LD
        if json_price:	# ✅ Є значення у JSON-LD
            logger.debug("💰 Ціна знайдена у JSON-LD: %s", json_price)	# 🪵 Джерело
            return json_price	# 🔁 Повертаємо значення

        meta_price = self.soup.select_one("meta[itemprop='price']")	# 🔍 Meta price
        if isinstance(meta_price, Tag) and meta_price.has_attr("content"):	# ✅ Валідний meta
            content = _norm_ws(str(meta_price.get("content") or ""))	# 🧼 Нормалізуємо
            if content:	# ✅ Контент існує
                logger.debug("💰 Ціна знайдена у meta[itemprop=price].")	# 🪵 Фіксуємо
                return content	# 🔁 Повертаємо значення

        for selector in self._S.PRICE_LIST:	# 🔁 Перебір DOM-селекторів
            price_el = self.soup.select_one(selector)	# 🔍 Шукаємо ціну
            if not price_el:	# ⛔️ Нема елементу
                continue	# 🔁 Далі
            try:
                text = cast(Tag, price_el).get_text(" ", strip=True)	# 🧾 Текст із елемента
            except Exception:	# ⚠️ Невдалий get_text
                text = str(price_el)	# 🔁 fallback
            normalized = _norm_ws(text)	# 🧼 Очищаємо
            match = re.search(r"[-+]?\d+(?:[.,]\d+)?", normalized)	# 🔍 Шукаємо числовий патерн
            if match:	# ✅ Знайшли число
                logger.debug("💰 Ціна знайдена селектором '%s'.", selector)	# 🪵 Фіксуємо джерело
                return match.group(0)	# 🔁 Повертаємо значення
            if normalized:	# ♻️ Віддаємо як є
                logger.debug("💰 Ціна повернена як текст для '%s'.", selector)	# 🪵 Повідомляємо
                return normalized	# 🔁 Текстовий fallback
        logger.warning("⚠️ Ціна не знайдена — повертаємо 0.0.")	# ⚠️ Інформація про fallback
        return 0.0	# 💰 Fallback значення

    # ================================
    # 🧾 ЗАЛИШКИ НА СКЛАДІ
    # ================================
    def extract_stock_from_json_ld(self) -> Optional[Dict[str, Dict[str, bool]]]:
        """📦 Повертає доступність варіантів з JSON-LD (offers)."""
        logger.debug("📦 Починаємо пошук наявності в JSON-LD.")	# 🪵 cтатус старту
        for idx, product in enumerate(self._json_ld_products(), start=1):	# 🔁 Всі товари з JSON-LD
            offers = product.get("offers")	# 📄 Блок offer(s)
            if not offers:	# ⛔️ Немає пропозицій
                logger.debug("📦 JSON-LD продукт #%d не містить offers.", idx)	# 🪵 Діагностика
                continue	# 🔁 Наступний товар
            stock_map = self._offers_to_stock_map(offers)	# 🗺️ Перетворення у карту наявності
            if stock_map:	# ✅ Успішна мапа
                logger.debug("📦 JSON-LD stock зібрано (%d товарів).", len(stock_map))	# 🪵 Статистика
                return stock_map	# 🔁 Повертаємо результат
        logger.info("ℹ️ JSON-LD не містить даних про наявність.")	# 📋 Інформуємо
        return None	# ⛔️ Дані відсутні

    def extract_stock_from_legacy(self) -> Optional[Dict[str, Dict[str, bool]]]:
        """📦 fallback-прохід по legacy-скриптах Shopify."""
        logger.debug("📦 Запускаємо legacy-прохід по Shopify скриптах.")	# 🪵 Старт діагностики
        scanned_scripts = 0	# 🔢 Лічильник опрацьованих скриптів
        payload = self.soup.select_one("script#ProductJson")	# 🧾 Класичний ProductJson
        if isinstance(payload, Tag):	# ✅ Маємо тег
            raw = (payload.string or payload.text or "").strip()	# 🧼 Сирі дані JSON
            obj = _try_json_loads(raw)	# 🧮 Парсимо JSON
            stock = self._shopify_variants_to_stock(obj)	# 🗺️ Мапа наявності
            if stock:	# ✅ Дані знайдено
                logger.debug("📦 Stock зчитано із script#ProductJson (%d варіантів).", len(stock))	# 🪵 Метрика
                return stock	# 🔁 Результат

        data_tag = self.soup.select_one('script[data-product-json="true"]')	# 🧾 Альтернативний тег
        if isinstance(data_tag, Tag):	# ✅ Є тег
            raw = (data_tag.string or data_tag.text or "").strip()	# 🧼 Сирий JSON
            obj = _try_json_loads(raw)	# 🧮 Парсимо
            stock = self._shopify_variants_to_stock(obj)	# 🗺️ Перетворюємо
            if stock:	# ✅ Є результат
                logger.debug("📦 Stock зчитано з data-product-json (%d варіантів).", len(stock))	# 🪵 Метрика
                return stock	# 🔁 Повертаємо

        for script in self.soup.find_all("script"):	# 🔁 Перебір усіх скриптів сторінки
            if not isinstance(script, Tag):	# ⛔️ Не тег
                continue	# 🔁 Пропускаємо
            text = (script.string or script.text or "").strip()	# 🧼 Зміст скрипта
            if not text:	# ⛔️ Порожній скрипт
                continue	# 🔁 Далі
            scanned_scripts += 1	# ➕ Збільшуємо лічильник
            mntn_obj = self._json_from_named_assignment(text, "mntn_product_data")	# 🏔️ Додаткове джерело Shopify
            if isinstance(mntn_obj, dict):	# ✅ Є JSON із Mountain тегу
                stock = self._shopify_variants_to_stock(mntn_obj)	# 🗺️ Перетворення в мапу
                if stock:	# ✅ Дані знайдено
                    logger.debug("📦 Stock витягнуто з mntn_product_data (%d варіантів).", len(stock))	# 🪵 Метрика
                    return stock	# 🔁 Повертаємо результат
            product_match = re.search(r"window\.Product\s*=\s*(\{.*?\});", text, re.S) or re.search(r"var\s+Product\s*=\s*(\{.*?\});", text, re.S)	# 🧪 Пошук визначення Product
            if product_match:	# ✅ Є payload
                stock = self._shopify_variants_to_stock(_try_json_loads(product_match.group(1)))	# 🗺️ Перетворення
                if stock:	# ✅ Вдалося зчитати
                    logger.debug("📦 Stock витягнуто з window.Product (%d варіантів).", len(stock))	# 🪵 Метрика
                    return stock	# 🔁 Повертаємо
            variants_match = re.search(r"var\s+Variants\s*=\s*(\[[\s\S]*?\])\s*;", text, re.S)	# 🧪 Масив варіантів
            if variants_match:	# ✅ Знайдено масив
                stock = self._variants_json_to_stock(variants_match.group(1))	# 🗺️ Перетворення
                if stock:	# ✅ Є результати
                    logger.debug("📦 Stock витягнуто з var Variants (%d варіантів).", len(stock))	# 🪵 Метрика
                    return stock	# 🔁 Повертаємо
        logger.info("ℹ️ Legacy-джерела Shopify не містять наявності (перевірено %d скриптів).", scanned_scripts)	# 📋 Інформаційне повідомлення
        return None	# ⛔️ Дані відсутні

    # ================================
    # 🛠️ ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _shopify_variants_to_stock(self, product_obj: Any) -> Optional[Dict[str, Dict[str, bool]]]:
        """🛠️ Будує мапу наявності з Shopify ProductJson."""
        if not isinstance(product_obj, dict):	# 🚫 Некоректний формат
            logger.debug("🛠️ Shopify JSON має неочікуваний тип: %s", type(product_obj).__name__)	# 🪵 Діагностика
            return None	# ⛔️ Дані відсутні
        variants = product_obj.get("variants")	# 🧾 Масив варіантів
        if not isinstance(variants, list):	# 🚫 Немає списку варіантів
            logger.debug("🛠️ Shopify JSON не містить списку variants.")	# 🪵 Пояснення
            return None	# ⛔️ Нічого повертати
        stock: Dict[str, Dict[str, bool]] = {}	# 📦 Результуюча мапа
        for variant in variants:	# 🔁 Обходимо кожен варіант
            if not isinstance(variant, dict):	# ⛔️ Некоректний запис
                continue	# 🔁 Пропускаємо
            color = str(variant.get("option1") or "DEFAULT").strip()	# 🟥 Варіація кольору
            size = str(variant.get("option2") or "DEFAULT").strip()	# 📏 Варіація розміру
            available = bool(variant.get("available", False))	# ✅ Флаг доступності
            stock.setdefault(color, {})[size] = available	# 🗂️ Оновлюємо мапу (nested dict)
        logger.debug("🛠️ Зібрано stock через Shopify-модель (%d кольорів).", len(stock))	# 🪵 Статистика
        return stock or None	# 🔁 Повертаємо результат або None

    def _variants_json_to_stock(self, payload: str) -> Optional[Dict[str, Dict[str, bool]]]:
        """🛠️ Будує мапу наявності з сирого JSON масиву варіантів."""
        obj = _try_json_loads(payload)	# 🧮 Парсимо JSON
        if not isinstance(obj, list):	# 🚫 Очікуємо список
            logger.debug("🛠️ Variants JSON має неочікуваний тип: %s", type(obj).__name__)	# 🪵 Попередження
            return None	# ⛔️ Некоректний формат
        stock: Dict[str, Dict[str, bool]] = {}	# 📦 Порожня мапа
        for variant in obj:	# 🔁 Кожен обʼєкт масиву
            if not isinstance(variant, dict):	# 🚫 Пропускаємо не-словники
                continue	# 🔁 Далі
            color = str(variant.get("option1") or "DEFAULT").strip()	# 🟥 Колір
            size = str(variant.get("option2") or "DEFAULT").strip()	# 📏 Розмір
            if not color or not size:	# ⚠️ Обовʼязкові поля
                continue	# ⛔️ Пропускаємо порожні значення
            available = bool(variant.get("available", False))	# ✅ Статус доступності
            stock.setdefault(color, {})[size] = available	# 🗂️ Оновлюємо мапу
        logger.debug("🛠️ Зібрано stock з масиву Variants (%d кольорів).", len(stock))	# 🪵 Діагностика
        return stock or None	# 🔁 Повертаємо результат

    @staticmethod
    def _json_from_named_assignment(script_text: str, identifier: str) -> Optional[Any]:
        """🧰 Вирізає JSON-обʼєкт із присвоєння `identifier = {...}`."""
        if identifier not in script_text:
            logger.debug("🧰 Ідентифікатор '%s' у скрипті не знайдено.", identifier)	# 🪵 Діагностика
            return None	# 🚫 Цільова змінна відсутня
        start_idx = script_text.find(identifier)
        assign_idx = script_text.find("=", start_idx)
        if assign_idx == -1:
            logger.debug("🧰 Ідентифікатор '%s' без оператора '='.", identifier)	# 🪵 Відсутній assignment
            return None	# 🚫 Немає оператору =
        brace_idx = None
        closer = ""
        for candidate, closing in (("{", "}"), ("[", "]")):
            pos = script_text.find(candidate, assign_idx)
            if pos != -1 and (brace_idx is None or pos < brace_idx):
                brace_idx = pos
                closer = closing
        if brace_idx is None:
            logger.debug("🧰 Не знайдено початок JSON для '%s'.", identifier)	# 🪵 Невдача пошуку
            return None	# 🚫 Не знайшли початок JSON
        stack: List[str] = [closer]	# 🧳 Стек очікуваних закриттів
        in_string = False
        escape = False
        for idx in range(brace_idx + 1, len(script_text)):
            ch = script_text[idx]
            if in_string:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == "\"":
                    in_string = False
                continue
            if ch == "\"":
                in_string = True
                continue
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack and ch == stack[-1]:
                stack.pop()
                if not stack:
                    raw_json = script_text[brace_idx : idx + 1]
                    logger.debug("🧰 JSON для '%s' знайдено (%d символів).", identifier, len(raw_json))	# 🪵 Фіксація успіху
                    return _try_json_loads(raw_json)
            else:
                continue
        logger.debug("🧰 Не вдалося завершити парсинг JSON для '%s'.", identifier)	# 🪵 Фінальна невдача
        return None	# 🚫 Дані не зчитані
