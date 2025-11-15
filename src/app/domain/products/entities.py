# 📦 app/domain/products/entities.py
"""
📦 Доменно-чисті сутності товарів із глибокою валідацією та логами.

🔹 Нормалізують назви, описи, медіа та складні структури (`sections`, `stock_data`).
🔹 Працюють лише з валідними типами (Decimal для ціни, int для грамів).
🔹 Усі сутності іммʼютабельні (frozen dataclass + mapping proxy).
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування всіх кроків валідації
from dataclasses import dataclass, field                            # 🧱 Опис сутностей
from decimal import Decimal, InvalidOperation                       # 💰 Робота з фінансовими даними
from enum import Enum                                               # 🔖 Переліки (Currency, Stage)
from types import MappingProxyType                                  # 🧊 Незмінні мапи
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple    # 🧰 Типізація
from urllib.parse import urlparse                                   # 🌐 Перевірка URL

# ================================
# 🪵 ЛОГЕР МОДУЛЯ
# ================================
logger = logging.getLogger(__name__)                                # 🧾 Модульний логер domain-level


# ================================
# 📏 КОНСТАНТИ ВАЛІДАЦІЇ
# ================================
TITLE_MAX_LEN = 200                                                 # 🏷️ Максимальна довжина заголовку
DESC_MAX_LEN = 2_000                                                # 📄 Ліміт опису
IMAGES_MAX = 50                                                     # 🖼️ Максимум картинок
SECTIONS_MAX = 20                                                   # 🗂️ Ліміт пар секцій
SECTION_KEY_MAX = 60                                                # 🔑 Ліміт ключа секції
SECTION_VAL_MAX = 2_000                                             # 🧾 Ліміт значення секції
WEIGHT_MIN = 0                                                      # ⚖️ Мінімальна вага (г)
WEIGHT_MAX = 200_000                                                # ⚖️ Максимальна вага (200 кг)


# ================================
# 🔗 VALUE OBJECT: URL
# ================================
@dataclass(frozen=True, slots=True)
class Url:
    """
    Іммʼютабельний value-object для абсолютних http(s) посилань.
    """

    value: str                                                      # 🌐 Канонічний URL

    def __post_init__(self) -> None:
        normalized = (self.value or "").strip()                     # 🧼 Trim + захист від None
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            logger.error("❌ Url: %r не є абсолютним http(s)", normalized)
            raise ValueError(f"Url must be absolute (http/https): {normalized!r}")
        object.__setattr__(self, "value", normalized)               # 🔐 Фіксуємо нормалізоване значення

    def __str__(self) -> str:
        return self.value                                           # 🧾 Зручно логувати/серіалізувати


# ================================
# 💱 ДОМЕННІ ТИПИ
# ================================
class Currency(str, Enum):
    """Підтримувані валюти товарів."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    PLN = "PLN"
    UAH = "UAH"


try:
    from app.domain.availability import AvailabilityStatus  # type: ignore  # 🔁 Використовуємо глобальний enum
except Exception:  # pragma: no cover
    class AvailabilityStatus(str, Enum):
        """Fallback-енум для статичного аналізу/тестів."""

        IN_STOCK = "in_stock"
        LOW_STOCK = "low_stock"
        OUT_OF_STOCK = "out_of_stock"
        UNKNOWN = "unknown"


Sections = Mapping[str, str]                                        # 🗂️ Секції опису товару
StockBySize = Mapping[str, AvailabilityStatus]                      # 👕 Розмір → статус
StockData = Mapping[str, StockBySize]                               # 🎨 Колір → (розміри → статус)


# ================================
# 🧊 ІММ'ЮТАБЕЛЬНІ МАПИ
# ================================
def _mp(data: Dict[str, Any]) -> MappingProxyType:
    """Створює `MappingProxyType`, щоби запобігти мутації після створення."""
    logger.debug("🧊 _mp: створюємо immutable proxy для %r", data)   # 🧊 Фіксуємо зміст мапи
    return MappingProxyType(data)                                   # 🔒 Повертаємо незмінний вигляд


# ================================
# 🧽 НОРМАЛІЗАЦІЙНІ ХЕЛПЕРИ
# ================================
def _clean_str(value: Any, *, max_len: int, default: str = "") -> str:
    """
    Trim + обрізання. Порожній результат → `default`.
    """
    raw = str(value or "").strip()                                 # 🧼 Приводимо до str і trim
    # 📭 Порожній рядок → фолбек
    if not raw:
        logger.debug("🧼 _clean_str: значення порожнє → %r", default)
        return default

    # ✂️ Перевищено ліміт → обрізаємо
    if len(raw) > max_len:
        logger.debug("✂️ _clean_str: %r → обрізано до %s символів", raw, max_len)
        return raw[:max_len]

    return raw                                                    # ✅ Валідне значення повертаємо як є


def _is_http_url(value: str) -> bool:
    """
    Перевіряє, чи є рядок валідним http(s) URL із netloc.
    """
    try:
        parsed = urlparse(value)                                   # 🔍 Парсимо URL
        valid = parsed.scheme in {"http", "https"} and bool(parsed.netloc)  # ✅ Схема + netloc обов'язкові
        if not valid:
            logger.debug("⚠️ _is_http_url: %r не валідний", value)
        return valid
    except Exception as exc:
        logger.debug("⚠️ _is_http_url: виняток %r для %r", exc, value)
        return False                                               # 🚫 Помилка парсингу → не валідно (не викликаємо exceptions вище)


def _uniq_keep_order(sequence: Iterable[str]) -> Tuple[str, ...]:
    """
    Повертає унікальні значення зі збереженням порядку.
    """
    result: list[str] = []                                         # 📦 Акумулятор унікальних значень
    seen: set[str] = set()                                         # 👀 Множина для швидкої перевірки
    for item in sequence or ():                                    # 🔁 Проходимо по колекції (може бути None)
        if item and item not in seen:                              # ✅ Беремо лише непорожні та нові значення
            result.append(item)
            seen.add(item)
    logger.debug("🔁 _uniq_keep_order: %r → %r", sequence, result)
    return tuple(result)                                           # 🔁 Зберігаємо порядок (tuple)


def _coerce_currency(value: Any, *, default: Currency = Currency.USD) -> Currency:
    """
    Дозволяє передати `Currency` або рядок; невідоме значення → `default`.
    """
    if isinstance(value, Currency):
        logger.debug("💱 _coerce_currency: отримано enum %s", value)
        return value                                               # ✅ Уже потрібний тип
    try:
        if isinstance(value, str) and value:
            coerced = Currency(value.upper().strip())
            logger.debug("💱 _coerce_currency: %r → %s", value, coerced)
            return coerced
    except Exception as exc:
        logger.debug("⚠️ _coerce_currency: %r не розпізнано (%r), фолбек %s", value, exc, default)
    logger.debug("💱 _coerce_currency: фолбек до %s", default)      # 🟡 Фолбек у разі невдачі
    return default


def _normalize_images(images: Iterable[str]) -> Tuple[str, ...]:
    """
    Очищає список зображень: лише http(s), uniq, ліміт `IMAGES_MAX`.
    """
    cleaned = [img.strip() for img in (images or ()) if isinstance(img, str)]  # 🧼 Trim + відкидаємо non-str
    cleaned = [img for img in cleaned if _is_http_url(img)]                    # 🌐 Лишаємо лише http(s)
    unique = _uniq_keep_order(cleaned)[:IMAGES_MAX]                            # 🔁 Унікальні з лімітом
    logger.debug("🖼️ _normalize_images: %r → %r", images, unique)
    return unique


def _normalize_sections(sections: Optional[Mapping[Any, Any]]) -> MappingProxyType:
    """
    Приводить до `Mapping[str, str]`, відкидає порожні/надто довгі значення, застосовує ліміт.
    """
    if not sections:
        logger.debug("🗂️ _normalize_sections: вхідні дані відсутні")
        return _mp({})
    normalized: Dict[str, str] = {}                               # 📦 Вихідна мапа
    for key, value in sections.items():                           # 🔁 Перебираємо пари
        normalized_key = _clean_str(key, max_len=SECTION_KEY_MAX, default="")   # 🔑 Тримаємо ключ у межах
        normalized_val = _clean_str(value, max_len=SECTION_VAL_MAX, default="") # 📄 Чистимо значення
        if normalized_key and normalized_val:
            normalized[normalized_key] = normalized_val            # ➕ Додаємо валідну пару
            if len(normalized) >= SECTIONS_MAX:
                logger.debug("🗂️ _normalize_sections: досягнуто ліміту %s", SECTIONS_MAX)
                break
    logger.debug("🗂️ _normalize_sections: %r → %r", sections, normalized)
    return _mp(normalized)


def _normalize_stock_data(stock: Optional[Mapping[Any, Mapping[Any, Any]]]) -> MappingProxyType:
    """
    Формує структуру {color: {size: AvailabilityStatus}} із очищенням ключів.
    """
    if not stock:
        logger.debug("📦 _normalize_stock_data: вхідні дані відсутні")
        return _mp({})
    normalized: Dict[str, Dict[str, AvailabilityStatus]] = {}      # 📦 Мапа кольорів
    for color, sizes in stock.items():                             # 🔁 Перебираємо кольори
        color_key = _clean_str(color, max_len=80, default="")      # 🎨 Нормалізуємо ключ color
        if not color_key or not isinstance(sizes, Mapping):
            continue
        normalized_sizes: Dict[str, AvailabilityStatus] = {}       # 👕 Мапа розмірів для конкретного кольору
        for size, status in sizes.items():                         # 🔁 Перебираємо розміри
            size_key = _clean_str(size, max_len=40, default="")    # 📏 Нормалізуємо розмір
            if not size_key:
                continue
            status_value: Optional[AvailabilityStatus] = None      # 🧾 Фінальний статус
            if isinstance(status, AvailabilityStatus):
                status_value = status
            elif isinstance(status, bool):
                status_value = AvailabilityStatus.YES if status else AvailabilityStatus.NO
            elif isinstance(status, str):
                try:
                    status_value = AvailabilityStatus(status)
                except Exception:
                    logger.debug("⚠️ _normalize_stock_data: статус %r не розпізнано", status)
            if status_value:
                normalized_sizes[size_key] = status_value          # 🆗 Додаємо валідний статус
        if normalized_sizes:
            normalized[color_key] = normalized_sizes               # 🔁 Додаємо блок кольору
    logger.debug("📦 _normalize_stock_data: %r → %r", stock, normalized)
    return _mp(normalized)


# ================================
# 🛍️ ОСНОВНА СУТНІСТЬ
# ================================
@dataclass(slots=True, frozen=True)
class ProductInfo:
    """
    Валідована, незмінна інформація про товар (price/weight/sections/stock).
    """

    title: str                                                      # 🏷️ Назва (обов'язкова)
    price: Decimal                                                   # 💰 Ціна
    description: str = "Опис відсутній"                             # 📄 Опис
    image_url: str = ""                                             # 🖼️ Головне зображення
    images: tuple[str, ...] = field(default_factory=tuple)          # 🖼️ Інші зображення
    sections: Sections = field(default_factory=lambda: _mp({}))     # 🗂️ Секції
    stock_data: StockData = field(default_factory=lambda: _mp({}))  # 📦 Наявність
    currency: Currency = Currency.USD                               # 💱 Валюта
    weight_g: int = 500                                             # ⚖️ Вага (грами)

    def __post_init__(self) -> None:
        # Назва
        normalized_title = _clean_str(self.title, max_len=TITLE_MAX_LEN, default="")   # 🧼 Чистимо заголовок
        if not normalized_title:
            logger.error("❌ ProductInfo: title порожній")
            raise ValueError("Назва товару (title) не може бути порожньою.")
        object.__setattr__(self, "title", normalized_title)                            # 🔐 Фіксуємо нормалізоване значення

        # Ціна
        try:
            normalized_price = Decimal(self.price)                                     # 💰 Перетворюємо в Decimal
        except (InvalidOperation, TypeError):
            logger.error("❌ ProductInfo: некоректна ціна %r", self.price)
            raise ValueError(f"Некоректне значення ціни: {self.price!r}")
        if normalized_price < 0:
            logger.error("❌ ProductInfo: ціна від'ємна %s", normalized_price)
            raise ValueError("Ціна не може бути від'ємною.")
        object.__setattr__(self, "price", normalized_price)                            # 📌 Зберігаємо валідовану ціну

        # Валюта
        coerced_currency = _coerce_currency(self.currency, default=Currency.USD)        # 💱 Коуерсимо валюту
        object.__setattr__(self, "currency", coerced_currency)

        # Вага
        try:
            raw_weight = int(self.weight_g)                                            # ⚖️ Переконуємось, що це int
        except (TypeError, ValueError):
            logger.error("❌ ProductInfo: weight_g не int (%r)", self.weight_g)
            raise ValueError(f"Некоректна вага (weight_g): {self.weight_g!r}")
        clamped_weight = max(WEIGHT_MIN, min(WEIGHT_MAX, raw_weight))                  # 🔒 Clamp у дозволені межі
        if clamped_weight != raw_weight:
            logger.debug("⚖️ ProductInfo: weight_g %s → clamp %s", raw_weight, clamped_weight)
        object.__setattr__(self, "weight_g", clamped_weight)

        # Опис
        normalized_description = _clean_str(                                           # 📄 Чистимо опис
            self.description,
            max_len=DESC_MAX_LEN,
            default="Опис відсутній",
        )
        object.__setattr__(self, "description", normalized_description)

        # Головне зображення
        normalized_image_url = (self.image_url or "").strip()                          # 🖼️ Trim для image_url
        if normalized_image_url and not _is_http_url(normalized_image_url):            # ❗ Лише валідні http(s)
            logger.debug("⚠️ ProductInfo: image_url %r не валідний → очищаємо", normalized_image_url)
            normalized_image_url = ""
        object.__setattr__(self, "image_url", normalized_image_url)

        # Галерея
        if self.images:
            normalized_images = _normalize_images(self.images)                         # 🖼️ Очищаємо та лімітуємо
            object.__setattr__(self, "images", normalized_images)

        # Секції
        if self.sections:
            normalized_sections = _normalize_sections(self.sections)  # type: ignore[arg-type]
            object.__setattr__(self, "sections", normalized_sections)                # 🗂️ Immutable mapping
        else:
            object.__setattr__(self, "sections", _mp({}))

        # Наявність
        if self.stock_data:
            normalized_stock = _normalize_stock_data(self.stock_data)  # type: ignore[arg-type]
            object.__setattr__(self, "stock_data", normalized_stock)                  # 📦 Immutable mapping
        else:
            object.__setattr__(self, "stock_data", _mp({}))

        logger.debug("✅ ProductInfo побудовано: %s", self.title)                      # ✅ Лог успішного створення

    def to_dict(self) -> Dict[str, Any]:
        """
        Серіалізатор у зручний dict (наприклад, для відповіді ботом).
        """
        payload = {
            "title": self.title,                                      # 🏷️ Назва
            "price": str(self.price),                                 # 💰 Decimal → str
            "description": self.description,                          # 📄 Опис
            "image_url": self.image_url,                              # 🖼️ Головне зображення
            "images": list(self.images),                              # 🖼️ Галерея
            "sections": dict(self.sections),                          # 🗂️ Секції
            "stock_data": {                                           # 📦 Наявність у читабельному форматі
                color: {size: status.value for size, status in sizes.items()}
                for color, sizes in self.stock_data.items()
            },
            "currency": self.currency.value,                          # 💱 Код валюти
            "weight_g": self.weight_g,                                # ⚖️ Вага
        }
        logger.debug("📤 ProductInfo.to_dict: %r", payload)
        return payload


__all__ = [
    "Url",
    "ProductInfo",
    "Currency",
    "Sections",
    "StockData",
    "StockBySize",
]
