# 📬 app/bot/ui/availability_messenger.py
"""
📬 availability_messenger.py — Відправка звітів про наявність у Telegram.

🔹 Клас `AvailabilityMessenger`:
- Відправляє користувачу заголовок з посиланням на товар
- Відправляє зображення товару (якщо є)
- Виводить публічний звіт і адмінський звіт
"""

# 🌐 Telegram API
from telegram import Update                                         # 📬 Оновлення від Telegram

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.availability.availability_processing_service import ProcessedAvailabilityData   # 📦 Оброблені дані наявності
from app.shared.utils.logger import LOG_NAME                                                          # 🧾 Імʼя логгера

# ================================
# 📬 МЕСЕНДЖЕР НАЯВНОСТІ
# ================================
logger = logging.getLogger(LOG_NAME)                                           # 🎯 Ініціалізація логгера

class AvailabilityMessenger:
    """
    📬 Відповідає за надсилання звітів про наявність у Telegram.
    """

    async def send(self, update: Update, data: ProcessedAvailabilityData):
        """
        📤 Відправляє фото/заголовок товару, публічний і адмінський звіти.

        Args:
            update (Update): 📬 Оновлення від Telegram
            data (ProcessedAvailabilityData): 📦 Оброблені дані (зображення, звіти, URL)
        """
        if not update.message:
            return                                                          # 🚫 Якщо повідомлення відсутнє — вихід

        caption = f"<b><a href='{data.header.product_url}'>{data.header.title}</a></b>"      # 🏷️ Заголовок із посиланням

        if data.header.image_url:
            await update.message.reply_photo(                               # 🖼️ Якщо є фото — надсилаємо як зображення
                photo=data.header.image_url,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(caption, parse_mode="HTML")    # 💬 Інакше просто текстом

        await update.message.reply_text(data.reports.public_report, parse_mode="HTML")   # 📢 Публічний звіт
        await update.message.reply_text(data.reports.admin_report, parse_mode="HTML")    # 🔒 Адмінський звіт

        logger.info(f"✅ Надіслано звіти про наявність для: {data.header.title}")           # 🧾 Логування успішного надсилання
