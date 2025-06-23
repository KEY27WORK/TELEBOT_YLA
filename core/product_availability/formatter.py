"""🎨 formatter.py — Форматування даних про наявність товару для Telegram."""

from typing import Dict

class ColorSizeFormatter:
    """🎨 Сервіс форматування кольорів і розмірів для відображення в Telegram."""
    # Мапа прапорців для відомих регіонів
    FLAGS = {
        "us": "🇺🇸",
        "eu": "🇪🇺",
        "uk": "🇬🇧",
        "ua": "🇺🇦"
    }

    @staticmethod
    def get_flag(region_code: str) -> str:
        """
        Повертає емодзі-прапор для заданого коду регіону (для невідомого коду повертає його верхній регістр).
        """
        if region_code in ColorSizeFormatter.FLAGS:
            return ColorSizeFormatter.FLAGS[region_code]
        if len(region_code) == 2 and region_code.isalpha():
            # Генеруємо прапор за дволітерним кодом країни (Unicode)
            return "".join(chr(0x1F1E6 + (ord(ch.upper()) - ord('A'))) for ch in region_code)
        return region_code.upper()

    @staticmethod
    def format_color_size_availability(color_data: Dict[str, Dict[str, bool]]) -> str:
        """
        📋 Форматує словник {колір: {розмір: наявність}} у зручний текстовий вигляд.
        ✅ Відображає лише розміри, які є в наявності.
        🚫 Якщо для кольору немає жодного доступного розміру — виводить 🚫.
        """
        result_lines = []
        for color, sizes in color_data.items():
            # Вибираємо тільки розміри, доступні (True)
            available_sizes = [size for size, available in sizes.items() if available]
            # Додаємо рядок для кожного кольору
            if not available_sizes:
                result_lines.append(f"• {color}: 🚫")
            else:
                result_lines.append(f"• {color}: {', '.join(available_sizes)}")
        return "\n".join(result_lines)

    @staticmethod
    def format_admin_availability(availability: Dict[str, Dict[str, list]], all_sizes_map: Dict[str, list]) -> str:
        """
        🦾 Форматує детальну карту наявності для адміністраторів.
        Показує для кожного розміру наявність (✅/🚫) у кожному регіоні (US, EU, UK, UA).
        Виводить навіть ті розміри, що відсутні всюди (позначаються 🚫 у всіх регіонах).
        :param availability: {color: {region: [sizes_available]}}
        :param all_sizes_map: {color: список усіх розмірів (у порядку появи)}
        """
        # Динамічно визначаємо актуальні регіони (UA додаємо окремо як відсутній регіон)
        from core.product_availability.availability_manager import AvailabilityManager
        regions = list(AvailabilityManager.REGIONS.keys()) + ["ua"]
        lines = []
        for color in all_sizes_map:
            lines.append(f"• {color}")
            all_sizes = all_sizes_map[color]
            for size in all_sizes:
                parts = [f"{size},"]
                for region in regions:
                    has_size = size in availability.get(color, {}).get(region, [])
                    parts.append(f"{ColorSizeFormatter.get_flag(region)} - {'✅' if has_size else '🚫'}")
                lines.append(" ".join(parts) + ";")
            lines.append("")  # порожній рядок після кожного кольору
        return "\n".join(lines)
