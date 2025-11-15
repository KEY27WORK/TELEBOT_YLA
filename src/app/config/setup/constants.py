# 📖 app/config/setup/constants.py
"""
📖 Типобезпечні константи Telegram-бота.

🔹 Централізує всі UI- та LOGIC-набори значень для інших модулів
🔹 Гарантує імутабельність через `dataclass(slots=True, frozen=True)`
🔹 Синхронізує ключі з YAML-конфігами та забезпечує legacy-API
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (зовнішніх залежностей у модулі немає)                               # 🚫 Немає сторонніх пакетів

# 🔠 Системні імпорти
import logging                                                         # 🧾 Логування подій ініціалізації констант
import re                                                              # 🔍 Побудова регулярних виразів для меню
from dataclasses import dataclass, fields                              # 🧱 Опис імутабельних структур
from functools import lru_cache                                        # ♻️ Кешування побудови callback-ів
from types import MappingProxyType                                     # 🧊 Імутабельні словники
from typing import TYPE_CHECKING, ClassVar, Final, List, Mapping        # 🧮 Типізація та підказки

# 🧩 Внутрішні модулі проєкту
if TYPE_CHECKING:                                                      # 🧪 Імпорт лише для типізації (уникаємо циклів)
    from app.bot.services.callback_data_factory import CallbackData    # 🏷️ Тип даних callback-ів

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger("app.config.constants")                     # 🧾 Модульний логер для діагностики


# ================================
# 🧰 ДОПОМІЖНІ ФУНКЦІЇ
# ================================
@lru_cache(maxsize=None)
def _build_callback(ns: str, name: str) -> "CallbackData":
    """
    Створює та кешує CallbackData для вказаного неймспейсу і ключа.
    """
    from app.bot.services.callback_data_factory import CallbackData     # 🧭 Локальний імпорт проти циклів

    logger.debug("🧱 Створюємо CallbackData ns=%s name=%s", ns, name)   # 🧾 Фіксуємо побудову callback-ключа
    return CallbackData(ns=ns, name=name)                               # 🏷️ Повертаємо кешований об'єкт


# ================================
# 🏛️ СТРУКТУРА КОНСТАНТ (UI)
# ================================
@dataclass(frozen=True, slots=True)
class _ReplyButtons:
    """Кнопки для ReplyKeyboardMarkup (головне меню)."""

    INSERT_LINKS: Final[str] = "🧾 Повний звіт по товару"               # 📩 Кнопка запиту повного аналізу
    MY_ORDERS: Final[str] = "📦 Мої замовлення"                          # 📦 Перехід до списку замовлень
    COLLECTION_MODE: Final[str] = "📚 Режим колекцій"                    # 🗃️ Активація пакетної обробки
    SIZE_CHART_MODE: Final[str] = "📏 Таблиця розмірів"                  # 📐 Режим пошуку таблиць
    CURRENCY: Final[str] = "💱 Курс валют"                               # 💱 Відкриття меню курсу валют
    HELP: Final[str] = "❓ Допомога"                                     # ❓ Довідка та FAQ
    PRICE_CALC_MODE: Final[str] = "🧮 Режим розрахунку товару"           # 🧮 Активація калькулятора цін
    REGION_AVAILABILITY: Final[str] = "🌍 Перевірити розміри в регіонах" # 🌍 Перевірка наявності за регіонами
    DISABLE_MODE: Final[str] = "⏹️ Вимкнути режим"                       # 🛑 Скидання активних режимів


@dataclass(frozen=True, slots=True)
class _InlineButtons:
    """Тексти для InlineKeyboardButton."""

    SHOW_RATE: Final[str] = "📊 Показати курс"                           # 📊 Показ значення курсу
    SET_RATE: Final[str] = "✏️ Встановити курс"                          # ✏️ Запуск зміни курсу
    HELP_FAQ: Final[str] = "📝 FAQ"                                      # 📝 Показ часто заданих питань
    HELP_USAGE: Final[str] = "📖 Як користуватись ботом?"                # 📖 Інструкція користувача
    HELP_SUPPORT: Final[str] = "📞 Зв'язатися з підтримкою"              # ☎️ Контакти підтримки


class _Callbacks:
    """Ліниві ключі для callback-запитів (використовує кеш _build_callback)."""

    __slots__ = ()

    @property
    def CURRENCY_SHOW_RATE(self) -> "CallbackData":
        logger.debug("💱 Отримуємо callback SHOW_RATE")                  # 🧾 Лог доступу до callback
        return _build_callback("currency", "show_rate")                  # 🏷️ Побудова ключа для показу курсу

    @property
    def CURRENCY_SET_RATE(self) -> "CallbackData":
        logger.debug("💱 Отримуємо callback SET_RATE")                   # 🧾 Лог доступу до callback
        return _build_callback("currency", "set_rate")                   # 🏷️ Побудова ключа для оновлення курсу

    @property
    def HELP_SHOW_FAQ(self) -> "CallbackData":
        logger.debug("❓ Отримуємо callback HELP_FAQ")                   # 🧾 Лог доступу до callback
        return _build_callback("help", "faq")                           # 🏷️ Повертаємо ключ FAQ

    @property
    def HELP_SHOW_USAGE(self) -> "CallbackData":
        logger.debug("📖 Отримуємо callback HELP_USAGE")                 # 🧾 Лог доступу до callback
        return _build_callback("help", "usage")                         # 🏷️ Повертаємо ключ інструкції

    @property
    def HELP_SHOW_SUPPORT(self) -> "CallbackData":
        logger.debug("☎️ Отримуємо callback HELP_SUPPORT")              # 🧾 Лог доступу до callback
        return _build_callback("help", "support")                       # 🏷️ Повертаємо ключ підтримки


@dataclass(frozen=True, slots=True)
class _UIConstants:
    """Константи UI (тексти, емодзі та parse mode)."""

    DEFAULT_PARSE_MODE: Final[str] = "HTML"                              # 📝 Форматування повідомлень за замовчуванням
    REPLY_BUTTONS: Final[_ReplyButtons] = _ReplyButtons()                # 🪟 Набір кнопок ReplyKeyboard
    INLINE_BUTTONS: Final[_InlineButtons] = _InlineButtons()             # 🧷 Набір кнопок InlineKeyboard


# ================================
# ⚙️ СТРУКТУРА КОНСТАНТ (LOGIC)
# ================================
@dataclass(frozen=True, slots=True)
class _Modes:
    """Ідентифікатори режимів роботи бота."""

    PRODUCT: Final[str] = "product"                                      # 🛒 Стандартний режим по товарах
    COLLECTION: Final[str] = "collection"                                # 🧺 Режим колекцій
    SIZE_CHART: Final[str] = "size_chart"                                # 📏 Розмірні таблиці
    REGION_AVAILABILITY: Final[str] = "region_availability"              # 🌍 Перевірка доступності в регіонах
    PRICE_CALCULATION: Final[str] = "price_calculation"                  # 🧮 Режим калькулятора


@dataclass(frozen=True, slots=True)
class _Commands:
    """Ідентифікатори команд Telegram-бота (без префікса '/')."""

    START: Final[str] = "start"                                          # ▶️ /start
    HELP: Final[str] = "help"                                            # ℹ️ /help
    RATE: Final[str] = "rate"                                            # 💱 /rate
    SET_RATE: Final[str] = "set_rate"                                    # ✏️ /set_rate


@dataclass(frozen=True, slots=True)
class _UserData:
    """Ключі для словника user_data (дані сеансу користувача)."""

    MODE: Final[str] = "mode"                                            # 🔀 Поточний режим користувача
    URL: Final[str] = "url"                                              # 🔗 Останнє опрацьоване посилання


@dataclass(frozen=True, slots=True)
class _Limits:
    """Ліміти для обробки."""

    MAX_PRODUCTS_PER_COLLECTION: Final[int] = 120                        # 📦 Максимум товарів у колекції
    COLLECTION_PROGRESS_EVERY: Final[int] = 5                            # ⏱️ Частота прогрес-логів


@dataclass(frozen=True, slots=True)
class _Timeouts:
    """Тайм-аути для операцій."""

    PRODUCT_PROCESS_SEC: Final[int] = 60                                 # 🕐 Обмеження на обробку товару


@dataclass(frozen=True, slots=True)
class _Conversions:
    """Коефіцієнти для конвертації одиниць."""

    LBS_PER_KG: Final[float] = 2.20462                                   # ⚖️ Фактор переводу з кг у фунти


@dataclass(frozen=True, slots=True)
class _LogicConstants:
    """
    Константи, що визначають логіку (режими, команди, ключі user_data, валюти, мапи).
    """

    ENV_PREFIX: Final[str] = "APP_"                                      # 🌐 Префікс змінних середовища
    MODES: Final[_Modes] = _Modes()                                      # 🧭 Контейнер ідентифікаторів режимів
    COMMANDS: Final[_Commands] = _Commands()                             # 🧾 Список команд бота
    USER_DATA: Final[_UserData] = _UserData()                            # 💾 Ключі user_data
    LIMITS: Final[_Limits] = _Limits()                                   # 🚦 Обмеження обробки
    TIMEOUTS: Final[_Timeouts] = _Timeouts()                             # ⏳ Тайм-аути
    CONVERSIONS: Final[_Conversions] = _Conversions()                    # ⚖️ Конвертаційні коефіцієнти

    CURRENCY_SYMBOLS: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "USD": "$",                                                  # 🇺🇸 Долар США
            "EUR": "€",                                                  # 🇪🇺 Євро
            "GBP": "£",                                                  # 🇬🇧 Фунт
            "PLN": "zł ",                                                # 🇵🇱 Злотий
            "UAH": "₴",                                                  # 🇺🇦 Гривня
        }
    )                                                                   # 🪙 Символи валют

    PRICE_ORDER: ClassVar[Mapping[str, List[str]]] = MappingProxyType(
        {
            "USD": ["USD", "UAH", "EUR", "GBP", "PLN"],                  # 🇺🇸 Пріоритет валют для базового USD
            "EUR": ["EUR", "UAH", "USD", "GBP", "PLN"],                  # 🇪🇺 Пріоритет валют для базового EUR
            "GBP": ["GBP", "UAH", "USD", "EUR", "PLN"],                  # 🇬🇧 Пріоритет валют для базового GBP
            "PLN": ["PLN", "UAH", "USD", "EUR", "GBP"],                  # 🇵🇱 Пріоритет валют для базового PLN
            "UAH": ["UAH", "USD", "EUR", "GBP", "PLN"],                  # 🇺🇦 Пріоритет валют для базового UAH
        }
    )                                                                   # 📊 Порядок відображення валют

    CURRENCY_TO_REGION: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "USD": "us",                                                # 🇺🇸 Відповідність регіону US
            "EUR": "eu",                                                # 🇪🇺 Відповідність регіону EU
            "GBP": "uk",                                                # 🇬🇧 Відповідність регіону UK
        }
    )                                                                   # 🌍 Мапа валют до регіонів config.yaml
    # ℹ️ PLN не має окремого region (користуємось mapping delivery/pricing)  # 📝 Пояснення пропуску PLN

    CURRENCY_MAP: ClassVar[Mapping[str, str]] = CURRENCY_TO_REGION       # 🔁 Алиас для legacy-коду

    CURRENCY_TO_DELIVERY_COUNTRY: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "USD": "us",                                                # 🚚 Meest: тариф для США
            "GBP": "uk",                                                # 🚚 Meest: тариф для Британії
            "EUR": "germany",                                           # 🚚 Meest: тариф для Німеччини
            "PLN": "poland",                                            # 🚚 Meest: тариф для Польщі
        }
    )                                                                   # 🧾 Мапа для delivery.yaml

    CURRENCY_TO_PRICING_COUNTRY_CODE: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "USD": "us",                                                # 💵 Pricing: US
            "EUR": "germany",                                           # 💶 Pricing: Germany
            "GBP": "uk",                                                # 💷 Pricing: UK
            "PLN": "poland",                                            # 💴 Pricing: Poland
        }
    )                                                                   # 🧮 Мапа для pricing.regional_costs


# ================================
# 🌍 ГОЛОВНИЙ ОБʼЄКТ КОНСТАНТ
# ================================
@dataclass(frozen=True, slots=True)
class AppConstants:
    """Єдина точка доступу до всіх констант проєкту (UI, LOGIC, CALLBACKS)."""

    UI: Final[_UIConstants] = _UIConstants()                             # 🧢 Блок UI-констант
    LOGIC: Final[_LogicConstants] = _LogicConstants()                    # ⚙️ Блок логічних констант
    CALLBACKS: Final[_Callbacks] = _Callbacks()                          # 🔗 Callback-ключі

    # ================================
    # 🧾 СЕРВІСНІ МЕТОДИ
    # ================================
    def get_all_reply_buttons(self) -> List[str]:
        """
        Повертає тексти всіх кнопок головного меню (Reply).
        """
        buttons: List[str] = []                                          # 📋 Колекція текстів кнопок
        for field in fields(self.UI.REPLY_BUTTONS):                      # 🔄 Ітеруємо всі поля ReplyButtons
            button_text = getattr(self.UI.REPLY_BUTTONS, field.name)     # 🧲 Зчитуємо конкретний текст кнопки
            buttons.append(button_text)                                  # ➕ Додаємо текст до результуючого списку
        logger.debug("📋 Reply buttons зібрано (%d шт.)", len(buttons))  # 🧾 Лог кількості кнопок
        return buttons                                                  # 🔁 Повертаємо список текстів

    def generate_menu_pattern(self) -> str:
        """
        Генерує regex-патерн для кнопок головного меню (Reply).
        """
        buttons = self.get_all_reply_buttons()                           # 📦 Отримуємо базовий список кнопок
        escaped_buttons: List[str] = []                                  # 🧼 Список екранованих текстів
        for text in buttons:                                             # 🔄 Екрануємо кожен напис кнопки
            escaped = re.escape(text)                                    # ✂️ Екрануємо спецсимволи
            escaped_buttons.append(escaped)                              # ➕ Додаємо екрановане значення
        pattern = f"^({'|'.join(escaped_buttons)})$"                     # 🧵 Будуємо патерн з варіантів
        logger.debug("🧵 Згенеровано меню-патерн %s", pattern)            # 🧾 Лог фінального патерну
        return pattern                                                   # 🔁 Повертаємо регулярний вираз


# ================================
# 🏁 ІНСТАНЦІЯ ТА ПУБЛІЧНИЙ API
# ================================
CONST = AppConstants()                                                  # 🧱 Єдиний екземпляр констант
logger.info("📖 AppConstants initialised")                              # 🧾 Фіксуємо ініціалізацію констант


def generate_menu_pattern() -> str:
    """
    Legacy-враппер для зворотної сумісності викликів.
    """
    logger.debug("♻️ Виклик legacy generate_menu_pattern()")             # 🧾 Лог звернення до враппера
    return CONST.generate_menu_pattern()                                # 🔁 Делегуємо основному методу


__all__ = ["AppConstants", "CONST", "generate_menu_pattern"]            # 📦 Публічний API модуля
