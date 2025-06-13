"""
📦 product_collection_handler.py — обробники товарів та колекцій для Telegram-бота YoungLA Ukraine.

🔹 Класи:
- `ProductHandler` — обробка окремих товарів (парсинг, ціни, опис, музика).
- `MusicSender` — відправка mp3-треків, кешування, групування.
- `CollectionHandler` — обробка колекцій (список товарів, регіон, виклик ProductHandler).

Використовує:
- Парсинг товарів і колекцій (ProductParser, CollectionParser)
- Генерацію опису, хештегів, музики
- Калькулятор цін (PriceCalculationHandler)
- Менеджер валют (CurrencyManager)
- Автоматичну обробку таблиці розмірів
- Відправку аудіо через Telegram
"""

# 🌐 Telegram API
from telegram import Update, InputMediaPhoto, InputMediaAudio
from telegram.constants import ChatAction
from telegram.ext import CallbackContext

# 🔊 Музика
from bot.music.music_sender import MusicSender
from bot.music.music_recommendation import MusicRecommendation

# 🧠 Генерація контенту
from bot.content.translator import TranslatorService
from bot.content.hashtag_generator import HashtagGenerator

# 🛍️ Парсинг товарів і колекцій
from core.parsing.parser_factory import ParserFactory
from core.parsing.base_parser import BaseParser

# 💰 Валюти та розрахунки
from core.currency.currency_manager import CurrencyManager
from core.calculator.calculator import PriceCalculatorFactory
from .price_calculation_handler import PriceCalculationHandler

# 📏 Таблиці розмірів
from size_chart.size_chart_handler import SizeChartHandler
from .size_chart_handler_bot import SizeChartHandlerBot

# 🛒 Наявність товару по регіонах
from core.parsing.availability_checker import AvailabilityChecker
from core.parsing.availability_aggregator import AvailabilityAggregator

# ⚙️ Інше
from bot.keyboards import Keyboard
from errors.error_handler import error_handler

# 🧱 Системні
import asyncio
import logging
import os

# 🧰 Утиліти
from utils.region_utils import get_region_from_url
from utils.url_utils import extract_product_path

# 📦 Моделі даних
from models.product_info import ProductInfo



class ProductHandler:
    """
    📦 Обробник товарних посилань у Telegram-боті.
    
    Основні функції:
    - Парсинг товару з сайту YoungLA
    - Розрахунок ціни (через PriceCalculationHandler)
    - Генерація опису, музики, хештегів
    - Надсилання результатів в Telegram
    """

    def __init__(self, currency_manager: CurrencyManager):
        self.currency_manager = currency_manager
        self.translator = TranslatorService()
        self.price_handler = PriceCalculationHandler(currency_manager)
        self.music_recommendation = MusicRecommendation()
        self.music_sender = MusicSender()
        self.hashtag_generator = HashtagGenerator()

    @error_handler
    async def handle_url(
        self, update: Update, context: CallbackContext,
        url: str = None, update_currency: bool = True
    ):
        """
        📥 Основний метод: отримує URL, обробляє товар, надсилає всі блоки повідомлень.
        """
        url = url or update.message.text.strip()
        if update_currency:
            self.currency_manager.update_rate()

        logging.info(f"📩 Отримано посилання: {url}")
            # 👇 ВСТАВИТЬ ЗДЕСЬ
        loading_msg = await update.message.reply_text("⏳ Завантаження товару...")
        for dots in ["⏳.", "⏳..", "⏳..."]:
            await asyncio.sleep(1.1)
            try:
                await loading_msg.edit_text(
                    f"{dots} Завантаження товару...\nЦе може зайняти до <b>30 секунд</b> через захист сайту 🛡️",
                    parse_mode="HTML"
                )
            except Exception:
                break

        parser = BaseParser(url)

        # 🌍 Логування регіону
        region_display = self._get_region_display(parser.currency)
        await update.message.reply_text(f"🌍 Регіон сайту: <b>{region_display}</b>", parse_mode="HTML")
        logging.info(f"🌍 Регіон сайту: {region_display}")

        # 📦 Парсимо товар
        product_info = await parser.get_product_info()

        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
        except Exception:
            pass
        
        if not isinstance(product_info, ProductInfo) or product_info.title == "Помилка":
            logging.error("❌ Не вдалося отримати повні дані про товар")
            await update.message.reply_text("⚠️ Помилка при отриманні інформації!")
            return

        await self._process_product(update, context, parser, url, product_info)

    # --- 🧠 Основна логіка обробки товару ---

    async def _process_product(self, update, context, parser, url, product_info):
        title = product_info.title
        price = product_info.price
        description = product_info.description
        image_url = product_info.image_url
        weight = product_info.weight
        images = product_info.images
        currency = product_info.currency
    
        # 🛒 Перевірка наявності в усіх регіонах (наличие самого товара)
        product_path = extract_product_path(url)
        availability_regions = await AvailabilityChecker.check(product_path)

        # 🧮 Новый блок: собираем объединенные размеры по регионам
        # 🚩 Формируем красивый текст цветов и размеров
        colors_text = await AvailabilityAggregator.aggregate_availability_formatted(product_path)

        # 🎶 Генеруємо текст музики і одразу запускаємо preload
        music_text = await self.music_recommendation.find_music(title, description, image_url)
        track_list = self.music_sender.parse_song_list(music_text)
        asyncio.create_task(self.music_sender.preload_tracks_async(track_list))
    
        # 🧠 Інші блоки — паралельно
        content_tasks = await asyncio.gather(
            asyncio.to_thread(self.translator.generate_slogan, title, description),
            self.hashtag_generator.generate(title, description),
            asyncio.to_thread(self.translator.translate_text, description),
            self.price_handler.calculate_and_format(url)
        )
    
        slogan, hashtags, sections, (region, price_message, images) = content_tasks
    
        # 📤 Відправка всіх блоків
        await self._send_all_blocks(
            update, context,
            title, colors_text, slogan, hashtags,
            sections, price_message, music_text,
            images, url, parser.page_source, availability_regions
        )
    
    # --- 📤 Відправка всіх блоків повідомлень ---

    async def _send_all_blocks(
        self, update, context, title, colors_text, slogan, hashtags,
        sections, price_message, music_text, images, url, page_source, availability_text
    ):

        title_upper = title.upper()

        await update.message.reply_text(
            self._build_description(title_upper, colors_text, slogan, hashtags, sections, availability_text),
            parse_mode="HTML"
        )
        await update.message.reply_text(title_upper, parse_mode="HTML")
        await update.message.reply_text(price_message, parse_mode="HTML")

        track_list = self.music_sender.parse_song_list(music_text)
        await self.music_sender.send_all_tracks(update, context, track_list)

        await self._send_images(update, images)
        await SizeChartHandlerBot.size_chart_command(update, context, url, page_source)

    # --- 🧩 Приватні допоміжні методи ---

    @staticmethod
    def _get_region_display(region: str) -> str:
        return {
            "USD": "🇺🇸 США",
            "EUR": "🇪🇺 Європа",
            "GBP": "🇬🇧 Британія",
            "PLN": "🇵🇱 Польща"
        }.get(region, region)

    @staticmethod
    def _build_description(title: str, colors_text: str, slogan: str, hashtags: str, sections: dict, availability_text: str) -> str:
        """
        📝 Побудова опису товару (характеристики + доступні регіони + кольори і розміри + хештеги).

        :param title: Назва товару
        :param colors_text: Кольори/розміри у вигляді тексту
        :param slogan: Слоган, згенерований AI
        :param hashtags: Хештеги
        :param sections: Перекладені блоки
        :param availability_text: Текст доступності по регіонах
        :return: HTML-текст повідомлення
        """
        
        material = sections.get("МАТЕРІАЛ", "Немає даних")  # 🧵 Матеріал
        fit = sections.get("ПОСАДКА", "Немає даних")        # 🪡 Посадка
        desc_text = sections.get("ОПИС", "Немає даних")     # 📜 Опис
        model = sections.get("МОДЕЛЬ", "Немає даних")       # 🧍 Модель
        
        # 🛒 Реальна перевірка на розпродаж
        sold_out = all("❌" in line for line in availability_text.splitlines())
    
        if sold_out:
            title = f"❌ РОЗПРОДАНО ❌\n\n{title.upper()}"
        else:
            title = title.upper()
    
        return (
            f"<b>{title}:</b>\n\n"
            f"<b>МАТЕРІАЛ:</b> {material}\n"
            f"<b>ПОСАДКА:</b> {fit}\n"
            f"<b>ОПИС:</b> {desc_text}\n\n"
            f"{availability_text}\n\n"
            f"<b>🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:</b>\n"
            f"{colors_text}\n\n"
            f"<b>МОДЕЛЬ:</b> {model}\n\n"
            f"<b>{slogan}</b>\n\n"
            f"<b>{hashtags}</b>"
        )

    @staticmethod
    async def _send_images(update: Update, images: list):
        if not images:
            await update.message.reply_text("⚠️ Зображення не знайдені!")
            return

        for i in range(0, len(images), 10):
            group = [InputMediaPhoto(img) for img in images[i:i + 10]]
            await update.message.reply_media_group(group)


class CollectionHandler:
    """
    🧾 Обробник колекцій товарів YoungLA:
    - Парсить посилання на колекцію
    - Визначає регіон сайту
    - Отримує всі товари в колекції
    - Використовує ProductHandler для обробки кожного товару

    ☑️ Відповідає принципам SOLID:
    - SRP: кожен метод виконує одну чітку задачу
    - DIP: використовує ProductHandler як залежність
    """

    def __init__(self, product_handler: ProductHandler = None, currency_manager: CurrencyManager = None):
        self.currency_manager = currency_manager or CurrencyManager()
        self.product_handler = product_handler or ProductHandler(self.currency_manager)

    @error_handler
    async def handle_collection(self, update: Update, context: CallbackContext):
        """
        📩 Основний метод — приймає посилання, обробляє колекцію товарів.
        """
        url = update.message.text.strip()
        logging.info(f"📩 Отримано посилання на колекцію: {url}")

        self.currency_manager.update_rate()  # 💱 Оновлюємо курси
        collection_parser = ParserFactory.get_collection_parser(url)  # 🧰 Парсер колекції
        region_display = get_region_from_url(url)  # 🌍 Визначаємо регіон

        await self.send_region_info(update, region_display)
        product_links = await collection_parser.extract_product_links()

        if not product_links:
            await update.message.reply_text("❌ Не вдалося знайти товари в цій колекції.")
            logging.warning("⚠️ Колекція порожня.")
            return

        await update.message.reply_text(f"🔍 Знайдено {len(product_links)} товарів. Починаю обробку...")

        await self.process_each_product(update, context, product_links)

        logging.info("✅ Завершено обробку всіх товарів з колекції.")

    async def send_region_info(self, update: Update, region: str):
        """
        🌍 Надсилає повідомлення з регіоном колекції (US/EU/UK).
        """
        await update.message.reply_text(f"🌍 Регіон колекції: <b>{region}</b>", parse_mode="HTML")
        logging.info(f"🌍 Регіон колекції: {region}")

    async def process_each_product(self, update: Update, context: CallbackContext, product_links: list[str]):
        """
        🔄 Обробляє кожен товар з колекції окремо.
        """
        for i, product_url in enumerate(product_links):
            logging.info(f"📦 Обробляю товар {i + 1}/{len(product_links)}: {product_url}")
            await self.product_handler.handle_url(update, context, product_url, update_currency=False)
            await asyncio.sleep(2)  # ⏳ Пауза між товарами
