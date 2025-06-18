# 📦 availability_handler.py — Перевірка наявності товару у регіонах (US, EU, UK, UA)

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 🛠️ Базова бізнес-логіка
from core.parsing.base_parser import BaseParser
from core.parsing.json_ld_parser import JsonLdAvailabilityParser
from core.parsing.color_size_formatter import ColorSizeFormatter

# ⚠️ Обробка помилок
from errors.error_handler import error_handler

# 🧱 Системні
import logging


class AvailabilityHandler:
    """
    📦 Обробник мульти-регіональної доступності товару.
    """

    def __init__(self):
        self.formatter = ColorSizeFormatter()

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основний виклик від Telegram (LinkHandler)
        """
        availability_data = await self._get_availability(url)

        public_format = self.formatter.format_color_size_availability(availability_data)
        admin_format = self._format_admin(availability_data)

        await update.message.reply_text(f"📦 <b>Доступність:</b>\n{public_format}", parse_mode="HTML")
        await update.message.reply_text(f"👨‍💻 <b>Детально по регіонах:</b>\n{admin_format}", parse_mode="HTML")

    async def calculate_and_format(self, url: str) -> tuple:
        """
        📦 Метод для ProductHandler
        """
        availability_data = await self._get_availability(url)

        public_format = self.formatter.format_color_size_availability(availability_data)
        admin_format = self._format_admin(availability_data)

        return "🌍 Мульти-регіон", public_format, admin_format

    async def _get_availability(self, url: str) -> dict:
        """
        🔄 Загальний метод обробки URL
        """
        parser = BaseParser(url)
        await parser.fetch_page()

        availability_data = JsonLdAvailabilityParser.extract_color_size_availability(parser.page_source)

        if not availability_data:
            # fallback если JSON-LD нет — пробуем вытянуть только цвета
            colors = await parser.extract_colors_from_html()
            availability_data = {color: {} for color in colors}

        logging.info(f"🔍 Отримано наявність товару по URL: {url}")
        return availability_data

    def _format_admin(self, availability: dict) -> str:
        """
        🧾 Форматування детального виводу для адмінів
        """
        lines = []

        for color, sizes in availability.items():
            lines.append(f"• {color}")
            for region in ["us", "eu", "uk", "ua"]:
                region_sizes = sizes.get(region, [])
                region_flag = self._region_to_flag(region)
                sizes_str = ", ".join(region_sizes) if region_sizes else "🚫"
                lines.append(f"  {region_flag}: {sizes_str}")
            lines.append("")  # Порожній рядок для читабельності

        return "\n".join(lines)

    @staticmethod
    def _region_to_flag(region: str) -> str:
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧", "ua": "🇺🇦"}
        return flags.get(region, region)
