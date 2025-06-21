"""
🔹 Клас `AvailabilityHandler`:
- Отримує посилання на товар
- Витягує шлях (`product_path`)
- Використовує AvailabilityManager для перевірки
- Формує публічний формат (простий вивід) та адмінський (по регіонах)

Використовує:
- extract_product_path() — для product_path
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 📦 Парсинг доступності
from core.parsing.availability_manager import AvailabilityManager

# 🔧️ Інфраструктура
from errors.error_handler import error_handler

# 🧠 Утиліти
from utils.url_utils import extract_product_path

# 🧱 Системні
import logging
import asyncio


class AvailabilityHandler:
    """
    📋 AvailabilityHandler — клас для перевірки наявності товару у всіх регіонах (US, EU, UK, UA).

    Відповідає за:
    - Обробку запитів користувача (через Telegram)
    - Формування двох форматів: публічного (кольори + розміри в наявності) і адмінського (по регіонах)
    - Виведення логів у консоль
    """

    def __init__(self):
        # 🏗️ Ініціалізуємо менеджер доступності, який відповідає за збір даних з різних регіонів
        self.manager = AvailabilityManager()

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основна точка входу. Отримує URL товару, перевіряє доступність і надсилає два повідомлення:
        - Публічний вивід
        - Адмінський вивід
        """
        product_path = extract_product_path(url)  # 🔗 Витягуємо шлях товару з URL

        # ✅ Коротка перевірка по регіонах — чи є взагалі в наявності хоч щось у кожному регіоні
        region_checks = await self.manager.check_simple_availability(product_path)

        # 🌍 Отримання детальної карти наявності: по кожному регіону окремо
        results = await asyncio.gather(*[
            self.manager._fetch_region_data(region_code, product_path)
            for region_code in self.manager.REGIONS
        ])

        # 🔁 Перетворення отриманих даних у дві структури:
        # - per_region — що є в наявності
        # - all_sizes_map — повний список розмірів (навіть якщо вони недоступні)
        per_region, all_sizes_map = self._group_by_region(results)

        # 🧮 Формування публічного виводу:
        # Збираємо тільки ті розміри, які є в наявності (загальна агрегація)
        merged_data = {
            color: sorted({size for region in per_region.get(color, {}) for size in per_region[color][region]})
            for color in all_sizes_map
        }
        public_format = self._get_public_format(merged_data)

        # 🧑‍💼 Формування розгорнутого адмінського виводу з усіма регіонами
        admin_format = self._format_admin(per_region, all_sizes_map)

        # 🖨️ Логування в консоль результатів для відлагодження
        logging.info("\U0001f4de Детальна карта по регіонах:")
        for color, region_sizes in per_region.items():
            logging.info(f"🎨 {color}")
            for region, sizes in region_sizes.items():
                logging.info(f"  {region.upper()}: {', '.join(sizes) if sizes else '🚫'}")

        # 📤 Надсилання результатів у Telegram (спочатку публічне, потім адмінське повідомлення)
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
        🔼 Публічний формат — список кольорів із доступними розмірами
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
        🧮 Адмінський формат — для кожного розміру показує статус наявності у кожному регіоні.
        Виводить навіть розміри, яких немає в наявності.

        :param availability: {color: {region: [sizes_available]}}
        :param all_sizes_map: {color: set(all_sizes)}
        :return: розгорнутий вивід для адмінів
        """
        lines = []
        all_regions = ["us", "eu", "uk", "ua"]  # Визначені регіони

        for color in all_sizes_map:
            lines.append(f"• {color}")
            all_sizes = sorted(all_sizes_map[color])  # 🔡 Всі розміри, незалежно від наявності

            for size in all_sizes:
                # 🏷️ Створення рядка: спочатку назва розміру, потім статуси по регіонах
                parts = [f"{size},"]
                for region in all_regions:
                    region_flag = self._region_to_flag(region)
                    has_size = size in availability.get(color, {}).get(region, [])
                    parts.append(f"{region_flag} - {'✅' if has_size else '🚫'}")
                lines.append(" ".join(parts) + ";")

            lines.append("")  # відступ між кольорами

        return "\n".join(lines)

    def _group_by_region(self, region_data: list[tuple[str, dict]]) -> tuple[dict, dict]:
        """
        🔁 Обробка даних з парсера: створює дві мапи
        - grouped: {color: {region: [sizes_with_stock]}} — доступні розміри по регіонах
        - all_sizes_map: {color: set(all_sizes)} — повний перелік розмірів (включно з відсутніми)
        """
        grouped = {}
        all_sizes_map = {}

        for region, data in region_data:
            for color, sizes in data.items():
                for size, is_available in sizes.items():
                    # 🧾 Зберігаємо всі розміри, незалежно від наявності
                    all_sizes_map.setdefault(color, set()).add(size)
                    if not is_available:
                        continue
                    # ✅ Додаємо лише доступні розміри у grouped
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
