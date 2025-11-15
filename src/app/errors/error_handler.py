# 🛠️ app/errors/error_handler.py
"""
🛠️ Фабрика декораторів для безпечного виконання async-хендлерів Telegram-бота.

🔹 Не змінює сигнатуру функції, працює з будь-якими *args/**kwargs.  
🔹 Коректно пропускає `asyncio.CancelledError`, щоб не ламати зупинку задач.  
🔹 Шукає обʼєкт `Update` серед аргументів і делегує винятки `ExceptionHandlerService`.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update											# 🤖 Telegram DTO

# 🔠 Системні імпорти
import asyncio														# ⏱️ CancelledError, event loop
import functools													# 🧱 wraps для збереження метаданих
import logging														# 🧾 Логи обробки помилок
from typing import Any, Callable, Coroutine, Optional				# 📐 Типи для сигнатур

# 🧩 Внутрішні модулі проєкту
from .exception_handler_service import ExceptionHandlerService		# 🛡️ Центральний сервіс обробки винятків


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger("app.errors.error_handler")				# 🧾 Локальний логер


# ================================
# 🔧 ТИПИ
# ================================
AsyncHandler = Callable[..., Coroutine[Any, Any, Any]]				# 🧾 Сумісний із Telegram/typedi


# ================================
# 🏭 ФАБРИКА ДЕКОРАТОРІВ
# ================================
def make_error_handler(service: ExceptionHandlerService) -> Callable[[AsyncHandler], AsyncHandler]:
    """
    Створює декоратор, замкнений на `ExceptionHandlerService`.

    Args:
        service: Сервіс, який отримує винятки і `Update`.

    Returns:
        Callable, що обгортає async-хендлери, додаючи централізовану обробку.
    """

    def decorator(func: AsyncHandler) -> AsyncHandler:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug("🧱 error_handler.wrapper start", extra={"handler": func.__name__})
            try:
                result = await func(*args, **kwargs)					# 🧠 Виконуємо оригінальний хендлер
                logger.debug("🟢 error_handler.wrapper success", extra={"handler": func.__name__})
                return result
            except asyncio.CancelledError:
                logger.info("⏹️ error_handler.cancelled", extra={"handler": func.__name__})
                raise													# ⚠️ Ніколи не глотаємо cancel
            except Exception as exc:									# noqa: BLE001
                update: Optional[Update] = kwargs.get("update")			# 🔍 Спочатку шукаємо в kwargs
                if update is None:										# 🔁 Інакше переглядаємо позиційні
                    for arg in args:
                        if isinstance(arg, Update):
                            update = arg
                            break
                logger.error(
                    "🔥 error_handler.exception",
                    extra={"handler": func.__name__, "has_update": update is not None},
                    exc_info=True,
                )
                await service.handle(exc, update)						# 🛡️ Передаємо в сервіс
                return None												# ↩️ Повертаємо None, як і раніше

        return wrapper													# type: ignore[return-value]

    return decorator													# 🧰 Сам декоратор для DI


__all__ = ["make_error_handler"]										# 📤 Публічний API
