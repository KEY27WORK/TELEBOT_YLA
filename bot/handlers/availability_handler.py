""" 📦 availability_handler.py — Перевірка наявності товару у регіонах (US, EU, UK)

🔹 Клас `AvailabilityHandler`:
- Отримує посилання на товар
- Витягує шлях (`product_path`)
- Викликає `check_availability_across_regions(return_dict=True)`
- Виводить формат для публікації та адмінів

Використовує:
- extract_product_path() — для product_path
- ColorSizeFormatter — для форматування
"""

# 🧱 Системні імпорти
import logging

# 🌐 Telegram
from telegram import Update
from telegram.ext import ContextTypes

# 🧠 Утиліти
from utils.url_utils import extract_product_path

from core.parsing.base_parser import BaseParser

from core.parsing.color_size_formatter import ColorSizeFormatter
from core.webdriver.webdriver_service import WebDriverService
from core.parsing.availability_checker import AvailabilityChecker

class AvailabilityHandler:
    """
    📋 Обробник перевірки наявності товару у всіх регіонах (US, EU, UK, UA)
    Працює через новий AvailabilityChecker та ColorSizeFormatter.
    """

    def __init__(self):
        self.formatter = ColorSizeFormatter()

    async def handle(self, product_url: str) -> tuple:
        """
        Основна точка входу — отримує URL товару, парсить доступність по регіонах,
        та формує обидва формати (публічний і адмінський).
        """
        webdriver_service = WebDriverService()
        checker = AvailabilityChecker(webdriver_service)
        availability = await checker.check_availability_across_regions(product_url)
        public_format = self.get_public_format(availability)
        admin_format = self.get_admin_format(availability)
        return public_format, admin_format

    def get_public_format(self, availability: dict) -> str:
        merged = self.formatter.merge_availability(availability)
        return "\n".join([
            f"• {color}: {', '.join(sizes)}" if sizes else f"• {color}: 🚫"
            for color, sizes in merged.items()
        ])

    def get_admin_format(self, availability: dict) -> str:
        lines = []

        for color in self.formatter._collect_all_colors(availability):
            lines.append(f"• {color}")
            for region in ["us", "eu", "uk", "ua"]:
                sizes = availability.get(region, {}).get(color, [])
                region_flag = self._region_to_flag(region)
                if sizes:
                    sizes_str = ", ".join(sizes)
                else:
                    sizes_str = "🚫"
                lines.append(f"  {region_flag}: {sizes_str}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _region_to_flag(region: str) -> str:
        flags = {
            "us": "🇺🇸",
            "eu": "🇪🇺",
            "uk": "🇬🇧",
            "ua": "🇺🇦",
        }
        return flags.get(region, region)