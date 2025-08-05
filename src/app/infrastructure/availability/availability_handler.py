# 📦 app/infrastructure/availability/availability_handler.py
"""
📦 availability_handler.py — Обробник перевірки наявності товару у Telegram.

🔹 Клас `AvailabilityHandler`:
    • Приймає URL товару та повідомлення Telegram
    • Делегує обробку та перевірку наявності `AvailabilityProcessingService`
    • Відправляє результат через `AvailabilityMessenger`
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update                                                   # 📬 Обʼєкт оновлення Telegram
from telegram.ext import CallbackContext                                     # ⚙️ Контекст колбеків

# 🧩 Внутрішні модулі проєкту
from .availability_processing_service import AvailabilityProcessingService   # 🧠 Обробка логіки перевірки
from app.bot.ui.availability_messenger import AvailabilityMessenger          # ✉️ Відправка повідомлень Telegram
from app.errors.error_handler import error_handler                           # 🛡️ Декоратор для обробки помилок


# ================================
# 🎯 ОБРОБНИК ПЕРЕВІРКИ НАЯВНОСТІ
# ================================
class AvailabilityHandler:
    """
    🎯 Делегує збір даних та відправку повідомлень відповідним сервісам.
    """

    def __init__(
        self,
        processing_service: AvailabilityProcessingService,
        messenger: AvailabilityMessenger
    ):
        self.processing_service = processing_service								# 🧠 Сервіс перевірки наявності
        self.messenger = messenger											# ✉️ Сервіс відправки повідомлень

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Обробляє посилання на товар, запускаючи процес перевірки та відправки.
        """
        if not update.message:
            return															# 🛑 Якщо повідомлення порожнє — нічого не робимо

        processed_data = await self.processing_service.process(url)					# 🔄 Отримуємо структуру з інформацією про наявність

        if not processed_data:
            await update.message.reply_text("⚠️ Не вдалося обробити посилання на товар.")		# ⚠️ Виводимо помилку користувачу
            return

        await self.messenger.send(update, processed_data)							# ✅ Відправляємо згенероване повідомлення
