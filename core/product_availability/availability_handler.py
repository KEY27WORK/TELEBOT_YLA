"""
🔹 Клас `AvailabilityHandler`:
- Отримує посилання на товар
- Витягує шлях (`product_path`)
- Використовує AvailabilityManager для перевірки наявності
- Формує публічний формат (список кольорів/розмірів) та адмінський (детально по регіонах)
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 📦 Логіка перевірки наявності
from core.product_availability.availability_manager import AvailabilityManager
from core.product_availability.formatter import ColorSizeFormatter
from core.parsers.base_parser import BaseParser

# 🛠️ Інфраструктура
from errors.error_handler import error_handler

# 🧰 Утиліти
from utils.url_utils import extract_product_path

# 🧱 Системні
import logging


class AvailabilityHandler:
    def __init__(self, manager: AvailabilityManager = None, formatter: ColorSizeFormatter = None):
        # Ініціалізація менеджера та форматера доступності (ін'єкція залежностей для гнучкості та тестування)
        self.manager = manager or AvailabilityManager()
        self.formatter = formatter or ColorSizeFormatter()

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основний метод: обробляє посилання на товар, перевіряє наявність і надсилає два повідомлення:
        - Публічний звіт (доступні кольори та розміри)
        - Адмінський звіт (детальна наявність по регіонах)
        """
        product_path = extract_product_path(url)
        # Отримуємо основну інформацію про товар (назва, фото) з US-сайту
        us_url = f"https://www.youngla.com{product_path}"
        parser = BaseParser(us_url)
        product_info = await parser.parse()
        title = product_info.get("title", "🔗 Товар").upper()
        image_url = product_info.get("image_url")

        logging.info(f"🛍️ Перевірка товару: {title}")
        if image_url:
            logging.info(f"🖼️ Головне зображення: {image_url}")

        # Отримуємо звіти про наявність товару
        availability_text = await self.get_availability_text(url)

        # Надсилаємо результати у Telegram
        if image_url:
            await update.message.reply_photo(photo=image_url, caption=title)
        else:
            await update.message.reply_text(title)
        # Публічний звіт (для користувача)
        await update.message.reply_text(
            availability_text["public_format"]
        )
        # Адмінський звіт (деталізація)
        await update.message.reply_text(
            availability_text["admin_format"]
        )

    async def get_availability_text(self, url: str) -> dict:
        """
        📦 Генерує готові HTML-звіти (публічний + адмінський) по URL товару.

        :param url: Повна URL-адреса товару
        :return: dict із ключами:
            - 'public_format': текст з кольорами/розмірами + регіональний чек
            - 'admin_format': деталізація по регіонах
        """
        product_path = extract_product_path(url)
        region_checks, public_format, admin_format = await self.manager.get_availability_report(product_path)

        return {
            "public_format": self.get_public_report_text(region_checks=region_checks, public_format=public_format),
            "admin_format":  self.get_admin_report_text(admin_format=admin_format),
        }

    def get_public_report_text(self, region_checks: str, public_format: str) -> str:
        """
        📄 Повертає HTML для публічного звіту:
        - Список регіонів (✅/❌)
        - Доступні кольори та розміри
        """

        return f"{region_checks}\n\n🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:\n{public_format}"

    def get_admin_report_text(self, admin_format: str) -> str:
        """
        👨‍🎓 Повертає HTML для адмінського звіту з деталізацією по регіонах.
        """

        return f"👨‍🎓 Детально по регіонах:\n{admin_format}"
