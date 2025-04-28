""" 🎨 color_size_formatter.py — Форматування кольорів і розмірів для Telegram.

🔹 Клас:
- `ColorSizeFormatter` — перетворює дані про кольори та розміри у форматований текст.

Використовує:
- Статичний метод для форматування доступності розмірів
"""

# 📦 Базові імпорти
from typing import Dict


class ColorSizeFormatter:
    """🎨 Сервіс форматування кольорів і розмірів для відображення в Telegram."""

    @staticmethod
    def format_color_size_availability(color_data: Dict[str, Dict[str, bool]]) -> str:
        """📋 Форматує словник {колір: {розмір: наявність}} у зручний вигляд.

        ✅ Показує лише доступні розміри  
        🚫 Якщо немає жодного розміру — показує заглушку

        :param color_data: Дані у форматі {color: {size: bool}}
        :return: Форматований рядок для Telegram
        """
        result = ""

        for color, sizes in color_data.items():
            available_sizes = [size for size, available in sizes.items() if available]

            if not available_sizes:
                result += f"• {color}: 🚫\n"
            else:
                result += f"• {color}: {', '.join(available_sizes)}\n"

        return result.strip()
