"""🎨 formatter.py — Форматування даних про наявність товару для Telegram."""

from typing import Dict

class ColorSizeFormatter:
    """🎨 Сервіс форматування кольорів і розмірів для відображення в Telegram."""

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
        :param all_sizes_map: {color: list усіх розмірів (у порядку появи)}
        """
        lines = []
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧", "ua": "🇺🇦"}
        regions = ["us", "eu", "uk", "ua"]
        for color in all_sizes_map:
            lines.append(f"• {color}")
            all_sizes = all_sizes_map[color]
            for size in all_sizes:
                parts = [f"{size},"]
                for region in regions:
                    has_size = size in availability.get(color, {}).get(region, [])
                    parts.append(f"{flags.get(region, region.upper())} - {'✅' if has_size else '🚫'}")
                lines.append(" ".join(parts) + ";")
            lines.append("")  # порожній рядок після кожного кольору
        return "\n".join(lines)
