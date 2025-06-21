"""
🔹 Клас `AvailabilityHandler`:
- Отримує посилання на товар
- Витягує шлях (`product_path`)
- Використовує AvailabilityManager для перевірки
- Формує публічний формат (простий вивід) та адмінський (по регіонах)

Використовує:
- extract_product_path() — для product_path
- ColorSizeFormatter — для форматування
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 📦 Парсинг доступності
from core.parsing.availability_manager import AvailabilityManager
from core.parsing.color_size_formatter import ColorSizeFormatter
from core.parsing.base_parser import BaseParser

# 🛠️ Інфраструктура
from errors.error_handler import error_handler

# 🧰 Утиліти
from utils.url_utils import extract_product_path

# 🧱 Системні
import logging
import asyncio


class AvailabilityHandler:
    def __init__(self):
        # Ініціалізуємо форматер і менеджер доступності
        self.formatter = ColorSizeFormatter()
        self.manager = AvailabilityManager()
        

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основна точка входу. Отримує URL товару, перевіряє доступність і надсилає два повідомлення:
        - Публічний вивід
        - Адмінський вивід
        """
        product_path = extract_product_path(url)
        # 🧠 Отримуємо назву товару та головне фото через BaseParser
        us_url = f"https://www.youngla.com{product_path}"  # ✅ формуємо повний URL
        parser = BaseParser(us_url)
        product_info = await parser.parse()

        title = product_info.get("title", "🔗 Товар").upper()
        image_url = product_info.get("image_url", None)

        # 🪪 Логування мета-даних
        logging.info(f"🛍️ {title}")
        if image_url:
            logging.info(f"🖼️ Фото: {image_url}")

        # ✅ Коротка перевірка по регіонах (прапорці)
        region_checks = await self.manager.check_simple_availability(product_path)

        # 🌍 Отримання детальної доступності по регіонах
        results = await asyncio.gather(*[
            self.manager._fetch_region_data(region_code, product_path)
            for region_code in self.manager.REGIONS
        ])
        per_region, all_sizes_map = self._group_by_region(results)

        # 🔁 Формування правильного public_format — тільки для розмірів, які реально в наявності
        merged_data = {}

        for color in all_sizes_map:
            sizes_in_order = list(all_sizes_map[color])  # ⬅️ Тут зберігається оригінальний порядок
            logging.info(f"всі розміри {sizes_in_order}")
            available_sizes = []

            for size in sizes_in_order:
                # Додаємо тільки ті розміри, які є в наявності в хоча б одному регіоні
                if any(size in per_region.get(color, {}).get(region, []) for region in per_region.get(color, {})):
                    available_sizes.append(size)

            merged_data[color] = available_sizes

        public_format = self._get_public_format(merged_data)

        admin_format = self._format_admin(per_region, all_sizes_map)

        # 🧾 Логування результатів
        logging.info("\U0001f4de Детальна карта по регіонах:")
        for color, region_sizes in per_region.items():
            logging.info(f"🎨 {color}")
            for region, sizes in region_sizes.items():
                logging.info(f"  {region.upper()}: {', '.join(sizes) if sizes else '🚫'}")

        # 📤 Надсилання результатів у Telegram
        if image_url:
            await update.message.reply_photo(photo=image_url, caption=title)
        else:
            await update.message.reply_text(title)
            
        await update.message.reply_text(
            f"{region_checks}\n\n<b>🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:</b>\n{public_format}",
            parse_mode="HTML"
        )
        await update.message.reply_text(
            f"<b>👨‍🎓 Детально по регіонах:</b>\n{admin_format}",
            parse_mode="HTML"
        )

    def _get_public_format(self, merged: dict) -> str:
        """
        🖼 Публічний формат — список кольорів із доступними розмірами
        :param merged: {color: [sizes]}
        :return: рядок для повідомлення
        """
        return "\n".join(
            [
                f"• {color}: {', '.join(sizes)}" if sizes else f"• {color}: 🚫"
                for color, sizes in merged.items()
            ]
        )

    def _format_admin(self, availability: dict, all_sizes_map: dict) -> str:
        """
        🦾 Адмінський формат — для кожного розміру показує статус наявності у кожному регіоні.
        Виводить навіть розміри, яких немає в наявності.

        :param availability: {color: {region: [sizes_available]}}
        :param all_sizes_map: {color: set(all_sizes)}
        :return: розгорнутий вивід для адмінів
        """
        lines = []
        all_regions = ["us", "eu", "uk", "ua"]

        for color in all_sizes_map:
            lines.append(f"• {color}")
            all_sizes = all_sizes_map[color]

            for size in all_sizes:
                parts = [f"{size},"]
                for region in all_regions:
                    region_flag = self._region_to_flag(region)
                    has_size = size in availability.get(color, {}).get(region, [])
                    parts.append(f"{region_flag} - {'✅' if has_size else '🚫'}")
                lines.append(" ".join(parts) + ";")

            lines.append("")  # пустий рядок після кожного кольору

        return "\n".join(lines)

    def _group_by_region(self, region_data: list[tuple[str, dict]]) -> tuple[dict, dict]:
        """
        🔁 Перетворює дані з fetch_region_data у зручну структуру:
        - grouped: {color: {region: [sizes_with_stock]}}
        - all_sizes_map: {color: list(all_sizes)} з унікальними розмірами у порядку першої появи
        """
        grouped = {}
        all_sizes_map = {}

        for region, data in region_data:
            for color, sizes in data.items():
                for size, is_available in sizes.items():
                    # ✅ Додаємо до списку розмірів, якщо ще не додано (з порядком)
                    if color not in all_sizes_map:
                        all_sizes_map[color] = []
                    if size not in all_sizes_map[color]:
                        all_sizes_map[color].append(size)

                    # ✅ Додаємо лише доступні розміри в grouped
                    if is_available:
                        grouped.setdefault(color, {}).setdefault(region, []).append(size)

        return grouped, all_sizes_map

    @staticmethod
    def _region_to_flag(region: str) -> str:
        """
        🏳️ Перетворює код регіону у відповідний прапор-емодзі
        :param region: us/eu/uk/ua
        :return: emoji
        """
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧", "ua": "🇺🇦"}
        return flags.get(region, region)
