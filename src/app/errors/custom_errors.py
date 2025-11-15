# 🚨 app/errors/custom_errors.py
"""
🚨 Deprecated-шлюз сумісності для старих імпортів.

🔹 Перенаправляє в новий модуль `app.shared.errors`, але зберігає старі імена.  
🔹 Підтримує `ErrorCode`, `ParsingError`, `NetworkRequestError`, щоб уникнути масових замін.  
🔹 Дає мінімальні лог-методи (`to_log_extra`) для плавної міграції.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (не використовуються)												# 🚫 Жодних сторонніх залежностей

# 🔠 Системні імпорти
import logging														# 🧾 Логування deprecated-шлюзу
from typing import Dict, Optional									# 📐 Типізація

# 🧩 Внутрішні модулі проєкту
from app.shared.errors import (										# 🔁 Перенаправлення на нову ієрархію
    AIError as AIError,
    AppError as AppError,
    UserVisibleError as UserVisibleError,
)


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger("app.errors.custom_errors")				# 🧾 Локальний логер


# ================================
# ⚠️ СТАРІ КОДИ ПОМИЛОК
# ================================
class ErrorCode:
    """⚠️ Мінімальна заглушка для зворотної сумісності."""

    AI = "ai_error"													# 🤖 AI-помилки
    PARSING = "parsing_error"										# 📄 Помилки парсингу
    NETWORK = "network_error"										# 🌐 Мережеві збої
    UNKNOWN = "unknown_error"										# ❓ Резервний код


# ================================
# 🧾 ДОДАТКОВІ ВИНЯТКИ
# ================================
class ParsingError(UserVisibleError):
    """🧾 Стара версія `ParsingError`, сумісна зі старим API."""

    def __init__(self, message: str, *, details: Optional[str] = None, url: Optional[str] = None) -> None:
        super().__init__(message, details=details)					# 🧠 Викликаємо базовий конструктор
        self.url = url												# 🔗 URL, де сталася помилка
        logger.debug("🧾 ParsingError created", extra={"url": url, "details": details})

    def to_log_extra(self) -> Dict[str, object]:
        """📦 Формує словник для логів (наслідуємо старий патерн)."""
        extra: Dict[str, object] = {"error_code": ErrorCode.PARSING}  # 🧾 Код помилки
        if self.url:													# 🔗 Додаємо URL за потреби
            extra["url"] = self.url
        return extra													# ↩️ Використовується в logger.extra


class NetworkRequestError(UserVisibleError):
    """🌐 Легасі-помилка мережевого запиту (для плавної міграції)."""

    def __init__(
        self,
        message: str,
        *,
        details: Optional[str] = None,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_after_s: Optional[int] = None,
    ) -> None:
        super().__init__(message, details=details)					# 🧠 Виклик базового конструктора
        self.url = url												# 🔗 URL, що викликав помилку
        self.status_code = status_code								# 🔢 HTTP-код відповіді
        self.retry_after_s = retry_after_s							# ⏳ Рекомендація щодо повторного запиту
        logger.debug(
            "🌐 NetworkRequestError created",
            extra={
                "url": url,
                "status_code": status_code,
                "retry_after_s": retry_after_s,
            },
        )

    def to_log_extra(self) -> Dict[str, object]:
        """📦 Формує словник для логування (сумісний з legacy-кодом)."""
        extra: Dict[str, object] = {"error_code": ErrorCode.NETWORK}	# 🌐 Категорія помилки
        if self.url:													# 🔗 Може додаватися URL
            extra["url"] = self.url
        if self.status_code is not None:								# 🔢 HTTP-код, якщо є
            extra["status_code"] = self.status_code
        if self.retry_after_s is not None:								# ⏳ Вказівка retry-after
            extra["retry_after_s"] = self.retry_after_s
        return extra													# ↩️ Для logger.extra


# ================================
# 📤 ПУБЛІЧНИЙ API
# ================================
__all__ = [
    "ErrorCode",													# ⚠️ Коди помилок
    "AppError",													# 🧠 Базове легасі-імʼя
    "UserVisibleError",											# 👀 Помилки, видимі користувачу
    "AIError",														# 🤖 AI-помилки
    "ParsingError",												# 🧾 Парсинг
    "NetworkRequestError",										# 🌐 Мережевий контекст
]
