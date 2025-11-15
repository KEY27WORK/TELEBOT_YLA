# 🧾 app/infrastructure/parsers/_infra_options.py
"""
🧾 Налаштування інфраструктурного шару парсерів.

🔹 Визначає іммутабельні опції (HTML-парсер, таймаути, ретраї, USer-Agent, локаль).
🔹 Підтримує зчитування з ENV (із автодетектом префікса) та мердж конфігів.
🔹 Експортує дефолтний обʼєкт `DEFAULT_PARSER_INFRA_OPTIONS` для швидкого використання.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging	# 🧾 Логування ініціалізації та валідації
import os	# 🌱 Зчитування ENV
from dataclasses import dataclass	# 🧱 Dataclass для опцій
from typing import Any, Dict, Literal, Mapping, Optional	# 🧰 Типи для статичного аналізу

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME	# 🏷️ Базове імʼя логера

# ================================
# 🧾 ЛОГЕР ТА КОНСТАНТИ
# ================================
logger = logging.getLogger(f"{LOG_NAME}.parsers.infra_options")	# 🧾 Модульний логер

_BOOL_TRUE = {"1", "true", "yes", "on", "y", "t"}	# ✅ Булеві true-представлення
_BOOL_FALSE = {"0", "false", "no", "off", "n", "f"}	# ❌ Булеві false-представлення

_LOG_LEVELS: Dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}	# 🎚️ Підтримувані рівні логів


# ================================
# 🛠️ ХЕЛПЕРИ КОНВЕРСІЙ
# ================================

def _parse_bool(val: Optional[str], default: bool) -> bool:
    """🔀 Перетворює ENV-рядок у bool з fallback."""
    if val is None:	# 🪣 Немає значення → дефолт
        return default
    cleaned = val.strip().lower()	# 🧼 Нормалізуємо кейс/пробіли
    if cleaned in _BOOL_TRUE:	# ✅ True-токени
        return True
    if cleaned in _BOOL_FALSE:	# ❌ False-токени
        return False
    logger.warning("⚠️ Некоректне булеве значення '%s' → fallback=%s.", val, default)	# 🪵 Попереджаємо
    return default	# 🪣 Повертаємо дефолт


def _to_int(val: Optional[str], default_val: int) -> int:
    """🔢 Конвертує рядок у int із захистом від помилок."""
    try:
        return int(val) if val is not None else default_val	# 🔢 Успішна конверсія
    except Exception:	# ⚠️ Некоректне значення
        logger.warning("⚠️ Неможливо перетворити '%s' у int → fallback=%s.", val, default_val)	# 🪵 Лог
        return default_val	# 🪣 Повертаємо дефолт


def _to_float(val: Optional[str], default_val: float) -> float:
    """🔢 Конвертує рядок у float із fallback."""
    try:
        return float(val) if val is not None else default_val	# 🔢 Успішна конверсія
    except Exception:	# ⚠️ Помилка конвертації
        logger.warning("⚠️ Неможливо перетворити '%s' у float → fallback=%s.", val, default_val)	# 🪵 Лог
        return default_val	# 🪣 Повертаємо дефолт


# ================================
# 🧱 МОДЕЛЬ ОПЦІЙ
# ================================
@dataclass(frozen=True, slots=True)
class ParserInfraOptions:
    """🧱 Іммутабельні параметри для всіх парсерів інфраструктури."""

    # Загальні опції
    html_parser: Literal["lxml", "html.parser", "html5lib"] = "lxml"	# 🥣 Дефолтний парсер DOM
    enable_progress: bool = True	# ⏳ Показувати прогрес
    request_timeout_sec: int = 30	# ⏱️ Таймаут запитів
    retry_attempts: int = 3	# 🔁 Кількість ретраїв
    retry_backoff_sec: float = 0.6	# ⏱️ Базовий бекофф
    min_html_bytes: int = 1000	# 📏 Мінімальний розмір HTML
    images_limit: int = 30	# 🖼️ Ліміт зображень
    filter_small_images: bool = True	# 🪟 Прибирати дрібні/плейсхолдери
    log_level: Optional[str] = None	# 🎚️ Додатковий рівень логів
    user_agent: Optional[str] = None	# 🕵️ Фіксований User-Agent
    locale: Optional[str] = None	# 🌍 Бажана локаль

    # 🔎 Пошук (IMP-030)
    search_goto_timeout_ms: int = 30_000
    search_idle_timeout_ms: int = 15_000
    search_predictive_timeout_ms: int = 7_000
    search_max_results_default: int = 10
    search_max_results_hardcap: int = 30
    search_retry_attempts: int = 2
    search_retry_backoff_ms: int = 600

    def __post_init__(self) -> None:
        """🛡️ Валідує інваріанти одразу після створення."""
        allowed_parsers = {"lxml", "html.parser", "html5lib"}	# ✅ Дозволені значення
        if self.html_parser not in allowed_parsers:
            raise ValueError(f"html_parser must be one of {allowed_parsers}, got: {self.html_parser!r}")
        if self.request_timeout_sec <= 0:
            raise ValueError("request_timeout_sec must be > 0")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be >= 0")
        if self.retry_backoff_sec <= 0:
            raise ValueError("retry_backoff_sec must be > 0")
        if self.min_html_bytes < 0:
            raise ValueError("min_html_bytes must be >= 0")
        if not (1 <= self.images_limit <= 200):
            raise ValueError("images_limit must be within [1, 200]")
        if self.log_level is not None:	# 🎚️ Перевіряємо рівень логів
            allowed_levels = set(_LOG_LEVELS.keys())
            if self.log_level.upper() not in allowed_levels:
                raise ValueError(f"log_level must be one of {allowed_levels}, got: {self.log_level!r}")
        if self.search_goto_timeout_ms <= 0:
            raise ValueError("search_goto_timeout_ms must be > 0")
        if self.search_idle_timeout_ms <= 0:
            raise ValueError("search_idle_timeout_ms must be > 0")
        if self.search_predictive_timeout_ms <= 0:
            raise ValueError("search_predictive_timeout_ms must be > 0")
        if self.search_max_results_default <= 0:
            raise ValueError("search_max_results_default must be > 0")
        if self.search_max_results_hardcap < self.search_max_results_default:
            raise ValueError("search_max_results_hardcap must be >= search_max_results_default")
        if self.search_retry_attempts < 0:
            raise ValueError("search_retry_attempts must be >= 0")
        if self.search_retry_backoff_ms <= 0:
            raise ValueError("search_retry_backoff_ms must be > 0")
        logger.debug("🛡️ ParserInfraOptions ініціалізовано з валідними значеннями.")	# 🪵 Підтвердження

    # ================================
    # 🧱 КОНСТРУКТОРИ
    # ================================
    @classmethod
    def default(cls) -> "ParserInfraOptions":
        """🧾 Повертає дефолтний набір опцій."""
        return cls()

    @classmethod
    def from_env(cls, prefix: str = "PARSER_") -> "ParserInfraOptions":
        """🌱 Будує опції з ENV (невідомі значення ігноруємо)."""
        defaults = cls.default()	# 🧱 Базові значення

        html_parser = os.getenv(f"{prefix}HTML_PARSER", defaults.html_parser)	# 🥣 Тип парсера
        enable_progress = _parse_bool(os.getenv(f"{prefix}ENABLE_PROGRESS"), defaults.enable_progress)	# ⏳ Прогрес
        request_timeout_sec = _to_int(os.getenv(f"{prefix}REQUEST_TIMEOUT_SEC"), defaults.request_timeout_sec)	# ⏱️ Таймаут
        retry_attempts = _to_int(os.getenv(f"{prefix}RETRY_ATTEMPTS"), defaults.retry_attempts)	# 🔁 Ретраї
        retry_backoff_sec = _to_float(os.getenv(f"{prefix}RETRY_BACKOFF_SEC"), defaults.retry_backoff_sec)	# ⏱️ Бекофф
        min_html_bytes = _to_int(os.getenv(f"{prefix}MIN_HTML_BYTES"), defaults.min_html_bytes)	# 📏 Обсяг HTML
        images_limit = _to_int(os.getenv(f"{prefix}IMAGES_LIMIT"), defaults.images_limit)	# 🖼️ Ліміт
        filter_small_images = _parse_bool(os.getenv(f"{prefix}FILTER_SMALL_IMAGES"), defaults.filter_small_images)	# 🪟 Фільтрація
        log_level = os.getenv(f"{prefix}LOG_LEVEL", defaults.log_level)	# 🎚️ Лог рівень
        user_agent = os.getenv(f"{prefix}USER_AGENT", defaults.user_agent)	# 🕵️ User-Agent
        locale = os.getenv(f"{prefix}LOCALE", defaults.locale)	# 🌍 Локаль

        s_goto = _to_int(os.getenv(f"{prefix}SEARCH_GOTO_TIMEOUT_MS"), defaults.search_goto_timeout_ms)	# 🔎 page.goto
        s_idle = _to_int(os.getenv(f"{prefix}SEARCH_IDLE_TIMEOUT_MS"), defaults.search_idle_timeout_ms)	# 🔎 idle
        s_pred = _to_int(os.getenv(f"{prefix}SEARCH_PREDICTIVE_TIMEOUT_MS"), defaults.search_predictive_timeout_ms)	# 🔎 predictive
        s_def = _to_int(os.getenv(f"{prefix}SEARCH_MAX_RESULTS_DEFAULT"), defaults.search_max_results_default)	# 🔎 default
        s_cap = _to_int(os.getenv(f"{prefix}SEARCH_MAX_RESULTS_HARDCAP"), defaults.search_max_results_hardcap)	# 🔎 hardcap
        s_ra = _to_int(os.getenv(f"{prefix}SEARCH_RETRY_ATTEMPTS"), defaults.search_retry_attempts)	# 🔎 ретраї
        s_rb = _to_int(os.getenv(f"{prefix}SEARCH_RETRY_BACKOFF_MS"), defaults.search_retry_backoff_ms)	# 🔎 бекофф

        logger.info("🌱 ParserInfraOptions зібрано з ENV (prefix=%s).", prefix)	# 🪵 Статистика
        return cls(
            html_parser=html_parser,  # type: ignore[arg-type]
            enable_progress=enable_progress,
            request_timeout_sec=request_timeout_sec,
            retry_attempts=retry_attempts,
            retry_backoff_sec=retry_backoff_sec,
            min_html_bytes=min_html_bytes,
            images_limit=images_limit,
            filter_small_images=filter_small_images,
            log_level=log_level,
            user_agent=user_agent,
            locale=locale,
            search_goto_timeout_ms=s_goto,
            search_idle_timeout_ms=s_idle,
            search_predictive_timeout_ms=s_pred,
            search_max_results_default=s_def,
            search_max_results_hardcap=s_cap,
            search_retry_attempts=s_ra,
            search_retry_backoff_ms=s_rb,
        )

    @classmethod
    def from_env_autodetect(
        cls,
        preferred_prefixes: tuple[str, ...] = ("YLA_PARSER_", "PARSER_"),
    ) -> "ParserInfraOptions":
        """🔍 Підбирає перший префікс із наявних у ENV; fallback → `PARSER_`."""

        def _has_any(prefix: str) -> bool:
            keys = (
                "HTML_PARSER","ENABLE_PROGRESS","REQUEST_TIMEOUT_SEC","RETRY_ATTEMPTS",
                "RETRY_BACKOFF_SEC","MIN_HTML_BYTES","IMAGES_LIMIT","FILTER_SMALL_IMAGES",
                "LOG_LEVEL","USER_AGENT","LOCALE",
                "SEARCH_GOTO_TIMEOUT_MS","SEARCH_IDLE_TIMEOUT_MS","SEARCH_PREDICTIVE_TIMEOUT_MS",
                "SEARCH_MAX_RESULTS_DEFAULT","SEARCH_MAX_RESULTS_HARDCAP",
                "SEARCH_RETRY_ATTEMPTS","SEARCH_RETRY_BACKOFF_MS",
            )	# 🗂️ Перелік ключів
            prefix_upper = prefix.upper()	# 🔡 Уніфікуємо регістр
            return any(f"{prefix_upper}{key}" in os.environ for key in keys)	# 🔍 Перевіряємо наявність хоч одного ключа

        for pref in preferred_prefixes:	# 🔁 Пріоритетний список
            if _has_any(pref):	# ✅ Знайшли відповідні змінні
                logger.info("🔍 Префікс %s знайдено в ENV.", pref)	# 🪵 Повідомляємо
                return cls.from_env(prefix=pref)	# 🔁 Збираємо опції
        logger.info("🔍 Префікси не знайдено, fallback на PARSER_.")	# 🪵 Інформація
        return cls.from_env(prefix="PARSER_")	# 🔁 Базовий префікс

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> "ParserInfraOptions":
        """🧾 Складання опцій із словника (зайві ключі ігноруються)."""
        if not data:	# 🪣 Порожній dict → дефолт
            return cls.default()	# 🧾 Повертаємо дефолт

        keys = {
            "html_parser",
            "enable_progress",
            "request_timeout_sec",
            "retry_attempts",
            "retry_backoff_sec",
            "min_html_bytes",
            "images_limit",
            "filter_small_images",
            "log_level",
            "user_agent",
            "locale",
            "search_goto_timeout_ms",
            "search_idle_timeout_ms",
            "search_predictive_timeout_ms",
            "search_max_results_default",
            "search_max_results_hardcap",
            "search_retry_attempts",
            "search_retry_backoff_ms",
        }	# 🗂️ Дозволені ключі
        kwargs: Dict[str, Any] = {key: data[key] for key in keys if key in data}	# 🧾 Фільтруємо ключі
        logger.debug("🧾 ParserInfraOptions.from_dict з ключами: %s", list(kwargs.keys()))	# 🪵 Статистика
        return cls(**kwargs)	# 🧱 Створюємо екземпляр

    # ================================
    # 🧰 УТИЛІТИ ЕКЗЕМПЛЯРА
    # ================================
    def merge(self, **overrides: Any) -> "ParserInfraOptions":
        """🔀 Повертає новий екземпляр із підмінними полями (immutability)."""
        base = self.to_kwargs()	# 🧾 Поточні значення
        base.update({key: value for key, value in overrides.items() if value is not None})	# 🧱 Перекриваємо
        logger.debug("🔀 merge overrides=%s", overrides)	# 🪵 Діагностика
        return ParserInfraOptions.from_dict(base)	# 🧱 Новий екземпляр

    def to_kwargs(self) -> Dict[str, Any]:
        """📦 Представляє опції як dict для подальшого передавання/логування."""
        return {
            "html_parser": self.html_parser,
            "enable_progress": self.enable_progress,
            "request_timeout_sec": self.request_timeout_sec,
            "retry_attempts": self.retry_attempts,
            "retry_backoff_sec": self.retry_backoff_sec,
            "min_html_bytes": self.min_html_bytes,
            "images_limit": self.images_limit,
            "filter_small_images": self.filter_small_images,
            "log_level": self.log_level,
            "user_agent": self.user_agent,
            "locale": self.locale,
            "search_goto_timeout_ms": self.search_goto_timeout_ms,
            "search_idle_timeout_ms": self.search_idle_timeout_ms,
            "search_predictive_timeout_ms": self.search_predictive_timeout_ms,
            "search_max_results_default": self.search_max_results_default,
            "search_max_results_hardcap": self.search_max_results_hardcap,
            "search_retry_attempts": self.search_retry_attempts,
            "search_retry_backoff_ms": self.search_retry_backoff_ms,
        }

    def effective_log_level(self) -> int:
        """🎚️ Повертає числовий logging level (за відсутності → INFO)."""
        if self.log_level is None:	# 🪣 Не заданий → INFO
            return logging.INFO
        return _LOG_LEVELS.get(self.log_level.upper(), logging.INFO)	# 🎚️ Конвертуємо текст у рівень


# ================================
# 📦 ГЛОБАЛЬНИЙ ДЕФОЛТ
# ================================
DEFAULT_PARSER_INFRA_OPTIONS = ParserInfraOptions.default()	# 📦 Базовий екземпляр

__all__ = ["ParserInfraOptions", "DEFAULT_PARSER_INFRA_OPTIONS"]	# 📦 Публічний експорт
