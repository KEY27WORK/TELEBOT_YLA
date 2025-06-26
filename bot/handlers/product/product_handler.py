"""
📦 ProductHandler — обробка окремих товарів у Telegram-боті YoungLA Ukraine.
🔹 Основні функції:
- Парсинг товару з сайту YoungLA
- Розрахунок ціни (через PriceCalculationHandler)
- Генерація опису, музики, хештегів (через ProductMessageBuilder та MusicRecommendation)
- Надсилання результатів в Telegram (через ImageSender та MusicSender)
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🔊 Музика
from bot.music.music_recommendation import MusicRecommendation
from bot.music.music_sender import MusicSender

# 🧠 Генерація контенту
from .product_message_builder import ProductMessageBuilder

# 🛍️ Парсинг товарів
from core.parsers.parser_factory import ParserFactory
from core.parsers.base_parser import BaseParser


# 🛒 Наявність товару по регіонах
from core.product_availability.availability_manager import AvailabilityManager
from core.product_availability.availability_handler import AvailabilityHandler

# 📦 Моделі даних
from models.product_info import ProductInfo

# 💰 Валюти та розрахунки
from core.currency.currency_manager import CurrencyManager

# 📏 Таблиці розмірів
from bot.handlers.size_chart_handler import SizeChartHandlerBot

# ⚙️ Інше
from errors.error_handler import error_handler
from .image_sender import ImageSender

# 🧱 Системні
import asyncio
import logging

logger = logging.getLogger(__name__)  # 👉 створюємо окремий логер для модуля

class ProductHandler:
    """
    📦 Обробник товарних посилань у Telegram-боті YoungLA Ukraine.

    🔹 Основні завдання:
    - Парсинг товару з сайту
    - Розрахунок ціни
    - Генерація опису, хештегів, музики
    - Відправка результатів у Telegram

    ☑️ Використовує:
    - ProductMessageBuilder — для генерації опису
    - MusicRecommendation / MusicSender — для підбору та надсилання треків
    - SizeChartHandlerBot — таблиці розмірів
    - ImageSender — надсилання зображень
    """

    def __init__(self, currency_manager: CurrencyManager, message_builder: ProductMessageBuilder = None, music_sender: MusicSender = None):
        """
        🔧 Ініціалізація залежностей:

        :param currency_manager: Менеджер валют для отримання курсів
        :param message_builder: Генератор повідомлень (можна передати кастомний)
        :param music_sender: Сервіс для надсилання треків (можна передати кастомний)
        """
        self.currency_manager = currency_manager
        self.message_builder = message_builder or ProductMessageBuilder(currency_manager)
        self.music_recommendation = MusicRecommendation()
        self.availability_handler = AvailabilityHandler()
        self.music_sender = music_sender or MusicSender()
        logger.info("🔧 Ініціалізовано ProductHandler")

    @error_handler
    async def handle_url(self, update: Update, context: CallbackContext, url: str = None, update_currency: bool = True):
        """
        📥 Основний метод: отримує URL товару, обробляє його та надсилає всі блоки повідомлень.
        """
        url = url or update.message.text.strip()
        if update_currency:
            self.currency_manager.update_rate()
        logger.info(f"📩 Отримано посилання: {url}")

        parser = ParserFactory.get_product_parser(url)
        # 🌍 Логування регіону сайту
        region_display = self._get_region_display(parser.currency)
        await update.message.reply_text(f"🌍 Регіон сайту: <b>{region_display}</b>", parse_mode="HTML")
        logger.info(f"🌍 Регіон сайту: {region_display}")

        # 📦 Парсимо товар
        product_info = await parser.get_product_info()

        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logger.error("❌ Не вдалося отримати повні дані про товар")
            await update.message.reply_text("⚠️ Помилка при отриманні інформації!")
            return
        logger.info(f"✅ Дані про товар успішно отримані: {product_info.title}")

        # 🔁 Продовжуємо обробку товару
        await self._process_product(update, context, parser, url, product_info)


    # --- 🧠 Основна логіка обробки товару ---
    async def _process_product(self, update: Update, context: CallbackContext, parser: BaseParser, url: str, product_info: ProductInfo):
        # 📋 Розпаковуємо основну інформацію про товар
        title = product_info.title
        description = product_info.description
        image_url = product_info.image_url
        # 🛒 Перевірка доступності по регіонах
        availability_text_dict = await self.availability_handler.get_availability_text(url)
        colors_text = availability_text_dict["public_format"]

        images = product_info.images

        logger.info(f"🧠 Генеруємо опис, ціну та музику для: {title}")

        # ⚙️ Паралельний запуск генерації контенту та пошуку музики
        content_future = self.message_builder.generate_content(title.upper(), description, image_url, url, colors_text)
        music_future = self.music_recommendation.find_music(title, description, image_url)

        try:
            content_result, music_text = await asyncio.gather(content_future, music_future)
            logger.info(f"✅ Контент та музика згенеровані для: {title}")
        except Exception as e:
            logger.error(f"🔥 Помилка при генерації контенту: {e}")
            await update.message.reply_text("⚠️ Помилка при створенні опису або музики.")
            return
        
        description_text, price_message, images = content_result

        # Надсилаємо всі блоки повідомлень з інформацією про товар
        await self._send_all_blocks(update, context, title, description_text, price_message, music_text, images, url, parser.page_source)

    # --- 📤 Відправка всіх блоків повідомлень ---
    async def _send_all_blocks(self, update: Update, context: CallbackContext, title: str, description_text: str, price_message: str, music_text: str, images: list, url: str, page_source: str):
        title_upper = title.upper()
        # Надсилаємо опис товару та деталі
        await update.message.reply_text(description_text, parse_mode="HTML")
        await update.message.reply_text(title_upper, parse_mode="HTML")
        await update.message.reply_text(price_message, parse_mode="HTML")
        logger.info(f"📨 Відправлено текстові блоки для: {title_upper}")

        # Відправляємо рекомендовані музичні треки
        if isinstance(music_text, str):
            try:
                track_list = self.music_sender.parse_song_list(music_text)
                await self.music_sender.send_all_tracks(update, context, track_list)
                logger.info(f"🎵 Музика надіслана для: {title_upper}")
            except Exception as e:
                logger.warning(f"🎵 Музика недоступна: {e}")
                await update.message.reply_text("🎵 Музика тимчасово недоступна.")
        else:
            logger.warning("🎵 Музика не згенерована або некоректна.")
            await update.message.reply_text("🎵 Музика тимчасово недоступна.")


        # Відправляємо зображення товару
        await ImageSender.send_images(update, images)
        logger.info(f"🖼️ Зображення надіслані: {len(images)} шт.")
        
        # Надсилаємо таблицю розмірів (як окрему команду бота)
        await SizeChartHandlerBot.size_chart_command(update, context, url, page_source)
        logger.info(f"📏 Таблиця розмірів надіслана для: {title_upper}")

    # --- 🧩 Приватні допоміжні методи ---
    @staticmethod
    def _get_region_display(region: str) -> str:
        """
        🌍 Повертає назву регіону з прапором за кодом валюти.
        """
        return {
            "USD": "🇺🇸 США",
            "EUR": "🇪🇺 Європа",
            "GBP": "🇬🇧 Британія",
            "PLN": "🇵🇱 Польща"
        }.get(region, region)
