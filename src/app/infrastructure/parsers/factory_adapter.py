# 🧾 app/infrastructure/parsers/factory_adapter.py
"""
🧾 Адаптер поверх ParserFactory, який повертає доменні інтерфейси парсерів.

🔹 Нормалізує посилання та обгортає сирі парсери у контракти `ICollectionLinksProvider` і `IProductDataProvider`.
🔹 Забезпечує безпечні фолбеки (titles/images) і мінімізує зайві мережеві виклики.
🔹 Додає україномовне логування для діагностики помилок парсингу.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import inspect	# 🧪 Визначаємо синхронні/асинхронні виклики
import logging	# 🧾 Глобальне логування адаптера
from typing import Any, List, Optional	# 🧰 Базові типи
from urllib.parse import urlparse, urlunparse	# 🔗 Робота з URL

# 🧩 Внутрішні модулі проєкту
from app.domain.products.dto import ProductHeaderDTO	# 🧾 Лайт-DTO заголовка
from app.domain.products.entities import ProductInfo, Url	# 📦 Доменно-типізовані сутності
from app.domain.products.interfaces import (	# 🤝 Контракти доменного рівня
    ICollectionLinksProvider,
    IProductDataProvider,
    IProductSearchProvider,
)
from app.infrastructure.parsers.contracts import IParserFactory	# 🤝 Контракт фабрики
from app.infrastructure.parsers.parser_factory import ParserFactory	# 🏭 Реалізація фабрики
from app.shared.utils.logger import LOG_NAME	# 🏷️ Базове імʼя логера

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.parsers.adapter")	# 🧾 Іменований логер адаптера

# ================================
# 🔗 НОРМАЛІЗАЦІЯ ПОСИЛАНЬ
# ================================


def _normalize_link(raw: str) -> str:
    """🔗 Приводить посилання до абсолютної HTTPS-форми або повертає порожній рядок."""
    if not isinstance(raw, str):	# 🚫 Очікуємо рядок
        logger.debug("🔗 Отримано не-рядок для нормалізації: %r", raw)	# 🪵 Діагностика
        return ""	# 🪣 Порожній результат

    trimmed = raw.strip()	# ✂️ Прибираємо пробіли
    if not trimmed:	# 🚫 Порожнє значення
        return ""	# 🪣 Не повертаємо нічого

    hash_pos = trimmed.find("#")	# 🔍 Шукаємо фрагмент
    if hash_pos != -1:	# ✅ Фрагмент присутній
        trimmed = trimmed[:hash_pos]	# ✂️ Відрізаємо частину після '#'

    if trimmed.startswith("//"):	# 🌐 Протокол-агностичні посилання
        trimmed = f"https:{trimmed}"	# 🔗 Примушуємо HTTPS

    lowered = trimmed.lower()	# 🔡 Для перевірки префіксів
    bad_prefixes = ("javascript:", "data:", "vbscript:", "mailto:", "tel:")	# 🚫 Небезпечні схеми
    if lowered.startswith(bad_prefixes):	# ⚠️ Заборонений префікс
        logger.debug("🔗 Посилання має небезпечний префікс: %s", trimmed)	# 🪵 Повідомляємо
        return ""	# 🪣 Ігноруємо

    try:
        parsed = urlparse(trimmed)	# 🧮 Парсимо URL
    except Exception as exc:	# ⚠️ Неможливо розпарсити
        logger.debug("🔗 Неможливо розпарсити посилання %s: %s", trimmed, exc)	# 🪵 Фіксуємо
        return ""	# 🪣 Fallback

    if parsed.scheme and parsed.scheme.lower() not in ("http", "https"):	# 🚫 Інші схеми
        return ""	# 🪣 Неприйнятно
    if not parsed.scheme or not parsed.netloc:	# 🚫 Відносні посилання
        return ""	# 🪣 Пропускаємо

    normalized = urlunparse(parsed._replace(fragment="")).strip()	# 🧼 Прибираємо фрагмент і збираємо назад
    base_len = len(f"{parsed.scheme}://{parsed.netloc}/")	# 📏 Довжина кореня
    if normalized.endswith("/") and len(normalized) > base_len:	# ✂️ Канонізуємо трейлінг слеш
        normalized = normalized[:-1]	# 🔁 Прибираємо «/»

    logger.debug("🔗 Нормалізація посилання: '%s' → '%s'.", raw, normalized)	# 🪵 Діагностика
    return normalized	# ✅ Повертаємо чистий URL


def _fallback_title_from_url(url: Url) -> str:
    """🏷️ Формує дружній заголовок із останнього сегмента URL."""
    try:
        tail = url.value.rstrip("/").split("/")[-1]	# ✂️ Беремо фінальний сегмент шляху
        friendly = tail.replace("-", " ").replace("_", " ").strip().capitalize()	# 🧼 Робимо читабельним
        fallback = friendly or url.value	# 🏷️ Повертаємо результат
        logger.debug("🏷️ Fallback title сформовано: %s → %s.", url.value, fallback)	# 🪵 Статистика
        return fallback
    except Exception as exc:	# ⚠️ Непередбачений збій
        logger.debug("🏷️ Неможливо згенерувати заголовок із URL %s: %s", url.value, exc)	# 🪵 Діагностика
        return "ТОВАР"	# 🏷️ Дефолт


# ================================
# 🔗 АДАПТЕР КОЛЕКЦІЙ
# ================================
class _LinksProviderAdapter(ICollectionLinksProvider):
    """🔗 Нормалізує списки товарних посилань і гарантує тип `Url`."""

    __slots__ = ("_inner",)	# 🧱 Зберігаємо лише обгорнутий парсер

    def __init__(self, inner: Any) -> None:
        self._inner = inner	# 🧩 Реальний парсер колекцій (фабричний)
        logger.debug("📚 _LinksProviderAdapter ініціалізовано (%s).", type(inner).__name__)	# 🪵 Фіксуємо

    async def get_product_links(self) -> List[Url]:
        """📦 Повертає список унікальних `Url` після нормалізації."""
        raw_links: List[str] = await self._inner.get_product_links() or []	# 🌐 Отримуємо сирі посилання
        seen: set[str] = set()	# ♻️ Відстежуємо дублікати
        normalized: List[str] = []	# 📦 Список очищених посилань

        for href in raw_links:	# 🔁 Обходимо всі посилання
            url_str = _normalize_link(href)	# 🔧 Нормалізуємо
            if not url_str:	# 🚫 Порожній результат
                continue	# 🔁 Далі
            if url_str in seen:	# ♻️ Вже зустрічалось
                continue	# 🔁 Пропускаємо дубль
            seen.add(url_str)	# 🗂️ Запамʼятовуємо
            normalized.append(url_str)	# 📦 Збираємо у список

        logger.info(
            "🔗 Колекція повернула %d посилань (%d після нормалізації) для %s.",
            len(raw_links),
            len(normalized),
            getattr(self._inner, "url", "unknown"),
        )	# 🪵 Статистика
        return [Url(link) for link in normalized]	# 🏷️ Перетворюємо на доменні Url


# ================================
# 🛒 АДАПТЕР ТОВАРУ
# ================================
class _ProductProviderAdapter(IProductDataProvider):
    """🛒 Узгоджує сирий парсер товару з доменним контрактом."""

    __slots__ = ("_inner", "url")	# 🧱 Тримаємо парсер і фінальний Url
    url: Url	# 🏷️ Public data-attribute (вимога Protocol)

    def __init__(self, inner: Any, url: Url) -> None:
        self._inner = inner	# 🧩 Сирий парсер товару
        self.url = url	# 🔗 Доменний URL

    async def get_product_info(self) -> ProductInfo:
        """📦 Делегує виклик реальному парсеру товару."""
        info = await self._inner.get_product_info()	# 🌐 Отримуємо повну інформацію
        logger.debug("🛒 ProductInfo отримано (url=%s).", self.url.value)	# 🪵 Фіксуємо факт
        return info	# 🔁 Повертаємо доменний обʼєкт

    async def get_header_info(self) -> ProductHeaderDTO:
        """🏷️ Повертає легку шапку товару з fallback-логікою."""
        hdr_callable = getattr(self._inner, "get_header_info", None)	# 🧰 Прагнемо легкий API

        if callable(hdr_callable):	# ✅ Реалізація підтримує header-info
            try:
                result = hdr_callable()	# 🔧 Викликаємо без await
                if inspect.iscoroutine(result):	# 🔄 Може бути корутина
                    result = await result	# ⏱️ Чекаємо виконання

                if isinstance(result, ProductHeaderDTO):	# ✅ Уже DTO
                    title = (result.title or "").strip() or "ТОВАР"	# 🏷️ Безпечний заголовок
                    image_url = (result.image_url or "").strip() or None	# 🖼️ Безпечний URL
                    logger.debug("🏷️ HeaderDTO отримано напряму (url=%s).", self.url.value)	# 🪵 Статистика
                    return ProductHeaderDTO(title=title, image_url=image_url, product_url=self.url)	# 🔁 DTO

                raw_title = result.get("title") if isinstance(result, dict) else getattr(result, "title", None)	# 🏷️ Альтернативні структури
                raw_image = result.get("image_url") if isinstance(result, dict) else getattr(result, "image_url", None)	# 🖼️ Альтернативні структури
                title_clean = (str(raw_title).strip() if raw_title is not None else "") or "ТОВАР"	# 🧼 Текст заголовку
                image_clean = (str(raw_image).strip() if raw_image else None) or None	# 🧼 URL зображення
                logger.debug("🏷️ HeaderDTO зібрано з довільної структури (url=%s).", self.url.value)	# 🪵 Статистика
                return ProductHeaderDTO(title=title_clean, image_url=image_clean, product_url=self.url)	# 🔁 DTO

            except Exception as exc:	# ⚠️ Помилка отримання хедера
                logger.warning(
                    "⚠️ get_header_info зірвався (url=%s inner=%s exc=%s msg=%s)",
                    self.url.value,
                    type(self._inner).__name__,
                    type(exc).__name__,
                    str(exc),
                )	# 🪵 Деталі проблеми
                return ProductHeaderDTO(
                    title=_fallback_title_from_url(self.url),	# 🏷️ Дружній fallback
                    image_url=None,	# 🖼️ Відсутнє зображення
                    product_url=self.url,	# 🔗 Зберігаємо URL
                )	# 🔁 DTO дефолт

        info = await self.get_product_info()	# 📦 Падаємо у повний ProductInfo
        title = (str(getattr(info, "title", "")).strip() or _fallback_title_from_url(self.url))	# 🧼 Заголовок із fallback
        image_raw = getattr(info, "image_url", None)	# 🖼️ Можливе зображення
        image_url = (str(image_raw).strip() if image_raw else None) or None	# 🧼 Приводимо до str
        logger.debug("🏷️ HeaderDTO побудовано з ProductInfo (url=%s).", self.url.value)	# 🪵 Статистика
        return ProductHeaderDTO(title=title, image_url=image_url, product_url=self.url)	# 🔁 DTO


# ================================
# 🏭 ПУБЛІЧНИЙ АДАПТЕР ФАБРИКИ
# ================================
class ParserFactoryAdapter(IParserFactory):
    """🏭 Обгортає `ParserFactory`, повертаючи доменні інтерфейси."""

    __slots__ = ("_inner",)	# 🧱 Тримаємо лише внутрішню фабрику

    def __init__(self, inner: ParserFactory) -> None:
        self._inner = inner	# 🏭 Зберігаємо реальну фабрику
        logger.debug("🏭 ParserFactoryAdapter ініціалізовано (%s).", type(inner).__name__)	# 🪵 Фіксуємо створення

    def create_collection_provider(self, url: Url) -> ICollectionLinksProvider:
        """📚 Створює провайдера колекцій із нормалізацією посилань."""
        parser = self._inner.create_collection_parser(url.value)	# 🏭 Отримуємо сирий парсер
        adapter = _LinksProviderAdapter(parser)	# 🔁 Обгортка
        logger.info("📚 Провайдер колекцій створено (url=%s, parser=%s).", url.value, type(parser).__name__)	# 🪵 Подія
        return adapter

    def create_product_provider(self, url: Url) -> IProductDataProvider:
        """🛒 Створює провайдера товару з fallback-логікою."""
        parser = self._inner.create_product_parser(url.value)	# 🏭 Отримуємо парсер товару
        adapter = _ProductProviderAdapter(parser, url)	# 🔁 Обгортка
        logger.info("🛒 Провайдер товару створено (url=%s, parser=%s).", url.value, type(parser).__name__)	# 🪵 Подія
        return adapter

    def create_search_provider(self) -> IProductSearchProvider:
        """🔍 Повертає доменний пошуковий провайдер (ProductSearchResolver)."""
        provider = self._inner.create_search_provider()	# 🏭 Фабрика віддає строгий resolver
        logger.info("🔍 Провайдер пошуку створено (%s).", type(provider).__name__)	# 🪵 Подія
        return provider	# 🔁 Повертаємо результат
