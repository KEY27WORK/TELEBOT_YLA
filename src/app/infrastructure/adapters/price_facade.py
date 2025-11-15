# 📬 app/infrastructure/adapters/price_facade.py
"""
📬 PriceMessageFacade — тонкий адаптер над `PriceCalculationHandler`.

🔹 Віддає чистий фасад без Telegram-залежностей: (ProductInfo, повідомлення, зображення).
🔹 Дає єдиний контракт `IPriceMessageFacade` для доменних/інфраструктурних сервісів.
🔹 Логує кожен виклик, щоб відстежувати використання `_calculate_and_format`.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (відсутні)															# 🚫 Лише стандартні типи

# 🔠 Системні імпорти
import logging															# 🧾 Логування фасада
from typing import Any, List, Protocol, Tuple							# 📐 Контракти та типи

# 🧩 Внутрішні модулі проєкту
from app.domain.products.entities import ProductInfo					# 📦 DTO товару
from app.shared.utils.logger import LOG_NAME							# 🏷️ Узгоджене імʼя логера


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai.price_facade")				# 🧾 Спеціальний логер адаптера


# ================================
# 🏛️ КОНТРАКТ ФАСАДА
# ================================
class IPriceMessageFacade(Protocol):
    """🏛️ Декларує мінімальний API для отримання повідомлення ціни."""

    async def calculate_and_format(self, url: str) -> Tuple[ProductInfo, str, List[str]]:
        """
        Args:
            url: Посилання на товар.

        Returns:
            ProductInfo, згенероване повідомлення, список зображень.
        """
        ...


# ================================
# 🧩 ФАСАД НАД ОБРОБНИКОМ
# ================================
class PriceMessageFacade(IPriceMessageFacade):
    """🧩 Обгортка над `PriceCalculationHandler._calculate_and_format` без Telegram-залежностей."""

    def __init__(self, handler: Any) -> None:
        self._handler = handler											# 🧠 Зберігаємо обробник
        logger.info("🧩 PriceMessageFacade init done")					# 🪵 Лог ініціалізації

    async def calculate_and_format(self, url: str) -> Tuple[ProductInfo, str, List[str]]:
        """
        Делегуємо в приватний метод, який вже реалізований у handler.

        Args:
            url: Посилання, для якого потрібно отримати звіт.
        """
        logger.debug("🧮 PriceMessageFacade.calculate_and_format", extra={"url": url})  # 🪵 Діагностика
        result = await self._handler._calculate_and_format(url)			# noqa: SLF001 # 👉 Використовуємо приватний метод

        if not isinstance(result, tuple) or len(result) != 3:
            logger.error(
                "❌ price_facade.invalid_result",
                extra={"url": url, "type": type(result).__name__},
            )
            raise ValueError("Handler must return (ProductInfo, str, List[str]) tuple.")

        product, message, images = result
        logger.debug(
            "📤 price_facade.success",
            extra={"url": url, "has_images": bool(images)},
        )																# 🪵 Підтверджуємо результат
        return product, message, list(images)							# ↩️ Строго типізована трійка


__all__ = ["IPriceMessageFacade", "PriceMessageFacade"]					# 📦 Публічний API
