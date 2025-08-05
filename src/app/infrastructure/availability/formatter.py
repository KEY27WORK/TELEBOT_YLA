# 🎨 app/infrastructure/availability/formatter.py
"""
🎨 formatter.py — Сервіс форматування карти наявності товарів.

🔹 Клас `ColorSizeFormatter`:
    • Форматує дані про наявність у публічному та адмінському форматі
    • Витягує перелік регіонів із конфігурації через DI
    • Підставляє прапори для кожного регіону
"""

# 🔠 Системні імпорти
from typing import Dict, List										# 🧰 Типізація для словників

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService					# ⚙️ Доступ до конфігурації регіонів


# ================================
# 🎨 КЛАС-ФОРМАТЕР
# ================================
class ColorSizeFormatter:
    """
    🎨 Сервіс форматування кольорів і розмірів для відображення в Telegram.
    """

    FLAGS = {
        "us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧", "ua": "🇺🇦"						# 🏳️ Прапори для стандартних регіонів
    }

    def __init__(self, config_service: ConfigService):
        """
        ✅ Ініціалізація з ConfigService для отримання списку регіонів.
        """
        self.regions = list(config_service.get("regions", {}).keys())				# 🗺️ Зберігаємо перелік регіонів з конфігу

    @staticmethod
    def get_flag(region_code: str) -> str:
        """
        🏳️ Повертає emoji-прапор за кодом країни (ISO Alpha-2).

        Args:
            region_code (str): Код регіону (напр. 'us')

        Returns:
            str: Прапор або великий код регіону
        """
        if region_code in ColorSizeFormatter.FLAGS:
            return ColorSizeFormatter.FLAGS[region_code]					# ✅ Відомий прапор
        if len(region_code) == 2 and region_code.isalpha():
            return "".join(chr(0x1F1E6 + (ord(ch.upper()) - ord('A'))) for ch in region_code)	# 🔠 Побудова прапора з Unicode
        return region_code.upper()									# 🅰️ fallback — просто великими літерами

    @staticmethod
    def format_public_report(merged_stock: Dict[str, Dict[str, bool]]) -> str:
        """
        📋 Форматує зведену карту наявності для публічного звіту.

        Args:
            merged_stock (dict): {'Black': {'S': True, 'M': False, ...}}

        Returns:
            str: Готовий текст для Telegram
        """
        result_lines = []
        for color, sizes in merged_stock.items():
            available_sizes = [size for size, available in sizes.items() if available]
            if not available_sizes:
                result_lines.append(f"• {color}: 🚫")									# ❌ Немає розмірів
            else:
                result_lines.append(f"• {color}: {', '.join(available_sizes)}")				# ✅ Доступні розміри
        return "\n".join(result_lines)

    def format_admin_report(
        self,
        availability: Dict[str, Dict[str, List[str]]],
        all_sizes_map: Dict[str, List[str]]
    ) -> str:
        """
        🦾 Форматує детальну карту наявності для адмінів по регіонах.

        Args:
            availability (dict): {'Black': {'us': ['M', 'L'], 'eu': ['S']}}
            all_sizes_map (dict): {'Black': ['S', 'M', 'L']}

        Returns:
            str: Деталізована таблиця для внутрішнього використання
        """
        regions_with_ua = self.regions + ["ua"]								# ➕ Додаємо локальний регіон в кінець списку
        lines = []

        for color, all_sizes in all_sizes_map.items():
            lines.append(f"• {color}")										# 🎨 Назва кольору
            for size in all_sizes:
                parts = [f"{size}:"]											# 📏 Назва розміру
                for region in regions_with_ua:
                    has_size = size in availability.get(color, {}).get(region, [])
                    parts.append(f"{ColorSizeFormatter.get_flag(region)} - {'✅' if has_size else '🚫'}")	# 🟢/🔴 по кожному регіону
                lines.append(" ".join(parts) + ";")							# ➕ Строка для розміру
            lines.append("")													# ↩️ Відступ між кольорами

        return "\n".join(lines)

    @property
    def format_color_size_availability(self):
        """
        ✅ Аліас для публічного методу (зворотна сумісність)
        """
        return self.format_public_report