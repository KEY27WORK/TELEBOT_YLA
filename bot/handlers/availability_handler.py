# 📦 availability_handler.py — Перевірка наявності товару у регіонах (US, EU, UK, UA)

from telegram import Update
from telegram.ext import CallbackContext

from core.parsing.availability_manager import AvailabilityManager
from core.parsing.color_size_formatter import ColorSizeFormatter
from errors.error_handler import error_handler
from utils.url_utils import extract_product_path

import logging
import asyncio


class AvailabilityHandler:
    """
    📦 Обробник мульти-регіональної доступності товару.
    """

    def __init__(self):
        self.formatter = ColorSizeFormatter()
        self.manager = AvailabilityManager()

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основний виклик від Telegram (LinkHandler)
        """
        product_path = extract_product_path(url)

        # 🔹 Булева карта доступності по регіонах (✅/❌)
        region_checks = await self.manager.check_simple_availability(product_path)

        # 🔹 Змерджена глобальна карта доступності (без поділу по регіонах)
        public_format = await self.manager.check_and_aggregate(product_path)
  

        # 🔹 Детальна карта доступності по регіонах
        results = await asyncio.gather(*[
            self.manager._fetch_region_data(region_code, product_path)
            for region_code in self.manager.REGIONS
        ])
        per_region = self._group_by_region(results)
        admin_format = self._format_admin(per_region)

        logging.info("🧾 Детальна карта по регіонах:")
        for color, region_sizes in per_region.items():
            logging.info(f"🎨 {color}")
            for region, sizes in region_sizes.items():
                logging.info(f"  {region.upper()}: {', '.join(sizes) if sizes else '🚫'}")

        await update.message.reply_text(
            f"{region_checks}\n\n<b>🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:</b>\n{public_format}",
            parse_mode="HTML"
        )
        await update.message.reply_text(
            f"👨‍💼 <b>Детально по регіонах:</b>\n{admin_format}",
            parse_mode="HTML"
        )

    async def calculate_and_format(self, url: str) -> tuple:
        """
        📦 Метод для ProductHandler
        """
        product_path = extract_product_path(url)
        region_checks = await self.manager.check_simple_availability(product_path)
        merged_data = await self.manager._aggregate_availability(product_path)
        public_format = self.formatter.format_color_size_availability(merged_data)

        results = await asyncio.gather(*[
            self.manager._fetch_region_data(region_code, product_path)
            for region_code in self.manager.REGIONS
        ])
        per_region = self._group_by_region(results)
        admin_format = self._format_admin(per_region)

        full_message = f"{region_checks}\n\n<b>🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:</b>\n{public_format}"
        return "🌍 Мульти-регіон", full_message, admin_format

    def _group_by_region(self, region_data: list[tuple[str, dict]]) -> dict:
        """
        🔄 Перетворює [(region, {color: {size: bool}}), ...] → {color: {region: [sizes]}}
        """
        grouped = {}

        for region, data in region_data:
            for color, sizes in data.items():
                for size, available in sizes.items():
                    if not available:
                        continue
                    grouped.setdefault(color, {}).setdefault(region, []).append(size)

        return grouped

    def _format_admin(self, availability: dict) -> str:
        """
        🦾 Форматування детального виводу для адмінів
        Очікує формат: {color: {region: [sizes]}}
        """
        lines = []

        for color, region_sizes_map in availability.items():
            lines.append(f"• {color}")
            for region in ["us", "eu", "uk", "ua"]:
                sizes = region_sizes_map.get(region, [])
                region_flag = self._region_to_flag(region)
                sizes_str = ", ".join(sizes) if sizes else "🚫"
                lines.append(f"  {region_flag}: {sizes_str}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _region_to_flag(region: str) -> str:
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧", "ua": "🇺🇦"}
        return flags.get(region, region)