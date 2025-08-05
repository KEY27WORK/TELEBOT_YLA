# 📬 app/bot/ui/product_messenger.py
"""
📬 product_messenger.py — сервіс для відправки скомплектованих повідомлень про товар.

🔹 Клас `ProductMessenger`:
- Відправляє текстові блоки (опис, ціна, назва)
- Генерує та надсилає музику
- Відправляє фото товару та таблицю розмірів
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update										                                            # 📩 Telegram-обʼєкти
from telegram.ext import CallbackContext						                                            # 🔁 Контекст виконання

# 🔠 Системні імпорти
import logging												                                                # 📝 Логування подій

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.image_sender import ImageSender			                                    # 🖼️ Відправка зображень
from app.bot.handlers.size_chart_handler_bot import SizeChartHandlerBot	                                    # 📏 Таблиці розмірів
from app.infrastructure.music.music_sender import MusicSender			                                    # 🎵 Надсилання треків
from app.infrastructure.product_processing.product_processing_service import ProcessedProductData	        # 🧠 DTO з обробленими даними
from app.shared.utils.logger import LOG_NAME					                                            # 📝 Назва логгера
from .message_formatter import MessageFormatter					                                            # 🧠 Форматування опису

logger = logging.getLogger(LOG_NAME)

# ================================
# 🏛️ КЛАС СЕРВІСУ ВІДПРАВКИ
# ================================
class ProductMessenger:
    def __init__(
        self,
        music_sender: MusicSender,								                                            # 🎵 Надсилання музики
        size_chart_handler: SizeChartHandlerBot,					                                        # 📏 Надсилання таблиць розмірів
        formatter: MessageFormatter,							                                            # 🧠 Форматування повідомлень
    ):
        self.music_sender = music_sender							                                        # 🎵 Сервіс музики
        self.size_chart_handler = size_chart_handler				                                        # 📏 Сервіс таблиць
        self.formatter = formatter								                                            # 🧠 Сервіс форматування

    async def send(self, update: Update, context: CallbackContext, data: ProcessedProductData):
        """
        📤 Відправляє всі згенеровані блоки (опис, ціна, музика, фото, таблиця розмірів).
        
        Args:
            update (Update): 📩 Об'єкт Telegram Update
            context (CallbackContext): 🔁 Контекст виклику
            data (ProcessedProductData): 🧠 DTO з усіма даними про товар
        """
        if not update.message:
            return

        title_upper = data.content.title.upper()						                                    # 🔠 Назва в верхньому регістрі
        description_text = self.formatter.format_description(data.content)                                  # 🧠 Формуємо HTML-опис

        # 1. Текстові блоки
        await update.message.reply_text(description_text, parse_mode="HTML")		                        # 📄 Опис товару
        await update.message.reply_text(f"<b>{title_upper}</b>", parse_mode="HTML")	                        # 🔠 Назва товару (жирна)
        await update.message.reply_text(data.content.price_message, parse_mode="HTML")	                    # 💸 Ціновий блок
        logger.info(f"📨 Текстові блоки відправлено для: {title_upper}")

        # 2. Музика
        await self._send_music_block(update, context, data.music_text, title_upper)

        # 3. Фото товару
        await ImageSender.send_images(update, data.content.images)			                                # 🖼️ Відправка зображень
        logger.info(f"🖼️ Відправлено {len(data.content.images)} зображень.")

        # 4. Таблиця розмірів
        await self.size_chart_handler.size_chart_command(update, context, data.url, data.page_source)	    # 📏 Надсилаємо таблицю розмірів
        logger.info(f"📏 Таблиця розмірів надіслана для: {title_upper}")

    async def _send_music_block(self, update: Update, context: CallbackContext, music_text: str, title: str):
        """
        🎵 Приватний метод для відправки музичного блоку з єдиною логікою обробки помилок.

        Args:
            update (Update): 📩 Обʼєкт Telegram Update
            context (CallbackContext): 🔁 Контекст Telegram
            music_text (str): 🎵 Сирий текст із треками
            title (str): 🔠 Назва товару (для логування)
        """
        if not music_text:
            logger.warning(f"🎵 Музика не згенерована для: {title}")
            return

        try:
            track_list = self.music_sender.parse_song_list(music_text)		                    # 🧩 Парсимо список треків
            await self.music_sender.send_all_tracks(update, context, track_list)	            # 📤 Надсилаємо всі треки
            logger.info(f"🎵 Музика надіслана для: {title}")
        except Exception as e:
            logger.warning(f"🎵 Помилка відправки музики: {e}")
            await update.message.reply_text("🎵 Музика тимчасово недоступна.")	                # 🛑 Fallback-повідомлення
