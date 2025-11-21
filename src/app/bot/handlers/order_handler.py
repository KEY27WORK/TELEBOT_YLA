# 📂 src/app/bot/handlers/order_handler.py
"""
📂 OrderFileHandler — приймає .txt зі SKU та викликає YoungLAOrderService.

🔹 Завантажує файл, безпечно декодує текст.
🔹 Делегує автоматизацію `YoungLAOrderService`.
🔹 Фіксує статус у логах і відповідає користувачу.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update

# 🔠 Системні імпорти
import asyncio
import logging

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext
from app.bot.ui import static_messages as msg
from app.errors.exception_handler_service import ExceptionHandlerService
from app.infrastructure.web.youngla_order_service import YoungLAOrderService
from app.shared.utils.logger import LOG_NAME


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)


# ================================
# 🏛️ ХЕНДЛЕР ФАЙЛІВ ЗАМОВЛЕНЬ
# ================================
class OrderFileHandler:
    """Обробляє .txt замовлення й делегує order-сервісу."""

    def __init__(
        self,
        order_service: YoungLAOrderService,
        exception_handler: ExceptionHandlerService,
    ) -> None:
        self._order_service = order_service
        self._exception_handler = exception_handler

    async def handle_order_file(self, update: Update, context: CustomContext) -> None:
        """Завантажує файл і запускає сервіс."""
        if not update.message or not update.message.document:
            return

        document = update.message.document
        filename = document.file_name or "orders.txt"
        user_id = update.effective_user.id if update.effective_user else "anonymous"
        logger.info(
            "📂 Отримано файл замовлення user=%s name=%s bytes=%s",
            user_id,
            filename,
            document.file_size,
        )

        try:
            await update.message.reply_text(
                msg.ORDER_FILE_RECEIVED.format(filename=filename),
            )
            file = await document.get_file()
            payload = await file.download_as_bytearray()
            file_text = self._decode_payload(payload)
            if not file_text.strip():
                await update.message.reply_text(msg.ORDER_FILE_NO_ITEMS)
                return

            await update.message.reply_text(msg.ORDER_FILE_PROCESSING)
            success = await self._order_service.process_order_file(file_text)
            await update.message.reply_text(
                msg.ORDER_FILE_SUCCESS if success else msg.ORDER_FILE_NO_ITEMS,
            )
        except asyncio.CancelledError:
            logger.warning("📂 OrderFileHandler cancelled user=%s", user_id)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("❌ Помилка OrderFileHandler user=%s", user_id)
            await update.message.reply_text(msg.ORDER_FILE_FAILED)
            await self._exception_handler.handle(exc, update)

    @staticmethod
    def _decode_payload(payload: bytes) -> str:
        """Декодує байти у текст із ігноруванням помилок."""
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("utf-8", errors="ignore")
