# 🎨 app/infrastructure/availability/formatter.py
"""
🎨 Форматує наявність товару за кольорами/розмірами для публічних і адмінських звітів.

🔹 `ColorSizeFormatter` отримує конфіг регіонів, забезпечує порядковість та прапори.  
🔹 Форматує публічний рядок (тільки YES/UNKNOWN) і детальний адмінський вигляд.  
🔹 Має fallback для старих викликів через `format_color_size_availability`.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування форматування
from typing import List, Mapping, Sequence                          # 📐 Типізація API

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                 # ⚙️ Конфіг регіонів
from app.domain.availability.sorting_strategies import default_size_sort_key  # 🔢 Ключ сортування
from app.domain.availability.status import AvailabilityStatus       # ✅ Enum YES/NO/UNKNOWN
from app.shared.utils.logger import LOG_NAME                        # 🏷️ Імʼя логера

logger = logging.getLogger(LOG_NAME)                                # 🧾 Модульний логер


# ================================
# 🎨 КЛАС-ФОРМАТЕР
# ================================
class ColorSizeFormatter:
    """🎨 Форматує перелік кольорів/розмірів для Telegram."""

    FLAGS = {
        "us": "🇺🇸",  # 🇺🇸 США
        "eu": "🇪🇺",  # 🇪🇺 ЄС
        "uk": "🇬🇧",  # 🇬🇧 Велика Британія
        "ua": "🇺🇦",  # 🇺🇦 Україна
    }

    def __init__(self, config_service: ConfigService) -> None:
        """Ініціалізує список регіонів із конфіга, фільтруючи службові ключі."""
        regions_cfg = config_service.get("regions") or {}            # 📒 Беремо секцію regions
        self.regions: List[str] = [
            code
            for code, value in regions_cfg.items()
            if code != "labels" and isinstance(value, dict)
        ]                                                             # 🗂️ Фільтруємо службові ключі
        logger.debug("⚙️ ColorSizeFormatter init (regions=%s)", self.regions)

    @staticmethod
    def get_flag(region_code: str) -> str:
        """🏳️ Повертає emoji-прапор за кодом регіону або generic fallback."""
        if not region_code:
            return "🏳️"                                            # 🏳️ Порожній код → білий прапор
        code = region_code.strip().lower()                           # 🔤 Уніфікуємо регіон
        if code in ColorSizeFormatter.FLAGS:
            return ColorSizeFormatter.FLAGS[code]                    # 🇺🇸 Відомий регіон
        if len(code) == 2 and code.isalpha():
            return "".join(chr(0x1F1E6 + (ord(ch.upper()) - ord("A"))) for ch in code)  # 🏴 Побудова прапора з букв
        return code.upper()                                          # 🔁 Fallback — верхній регістр

    @staticmethod
    def human_flag(status: AvailabilityStatus) -> str:
        """🧭 Перетворює статус у зрозумілий символ."""
        if status is AvailabilityStatus.YES:
            return "✅"                                              # ✅ Є в наявності
        if status is AvailabilityStatus.NO:
            return "🚫"                                              # 🚫 Немає
        return "❔"                                                   # ❔ Unknown / немає даних

    def format_public_report(
        self,
        merged_stock: Mapping[str, Mapping[str, AvailabilityStatus]],
    ) -> str:
        """📢 Форматує загальний звіт, показуючи лише YES або стан по кольору."""
        colors_sorted = sorted(merged_stock.keys(), key=lambda s: s.upper())  # 🔠 Стабільний порядок кольорів
        result_lines: List[str] = []                                          # 📝 Результат для Telegram

        for color in colors_sorted:
            sizes_map = merged_stock.get(color, {})                   # 🎨 Карта розмірів для кольору
            size_keys = sorted(sizes_map.keys(), key=default_size_sort_key)  # 📏 Стабільний порядок розмірів
            yes_sizes = [sz for sz in size_keys if sizes_map.get(sz) is AvailabilityStatus.YES]
            any_unknown = any(sizes_map.get(sz) is AvailabilityStatus.UNKNOWN for sz in size_keys)

            if yes_sizes:
                result_lines.append(f"• {color}: {', '.join(yes_sizes)}")
            else:
                result_lines.append(f"• {color}: {'❔' if any_unknown else '🚫'}")
            logger.debug("🎨 Публічний рядок для %s: %s", color, result_lines[-1])

        return "\n".join(result_lines)

    def format_admin_report(
        self,
        availability: Mapping[str, Mapping[str, Sequence[str]]],
        all_sizes_map: Mapping[str, Sequence[str]],
    ) -> str:
        """🛠 Форматує детальну карту наявності для адмінів."""
        regions_with_ua = sorted(self.regions) + (["ua"] if "ua" not in self.regions else [])  # 🗺️ Фіксуємо порядок регіонів
        lines: List[str] = []                                        # 📜 Збираємо текст рядок за рядком

        for color in sorted(all_sizes_map.keys(), key=lambda s: s.upper()):
            all_sizes = list(all_sizes_map.get(color, []))            # 📦 Усі відомі розміри для кольору
            if all_sizes != sorted(all_sizes, key=default_size_sort_key):  # 🧮 Пересортовуємо за доменним правилом
                all_sizes = sorted(all_sizes, key=default_size_sort_key)

            lines.append(f"• {color}")                                        # 🎨 Виводимо назву кольору
            for size in all_sizes:
                parts = [f"{size}:"]                                         # 📏 Початок рядка зі значенням розміру
                for region in regions_with_ua:
                    has_size = size in (availability.get(color, {}).get(region, []) or [])  # ✅ Перевіряємо наявність
                    parts.append(f"{self.get_flag(region)} - {'✅' if has_size else '🚫'}")
                formatted_line = " ".join(parts) + ";"
                lines.append(formatted_line)
                logger.debug("🧾 Адмінрядок: %s", formatted_line)
            lines.append("")                                                # ↩️ Порожній рядок між кольорами

        return "\n".join(lines)

    @property
    def format_color_size_availability(self):
        """🔁 Зворотна сумісність зі старими викликами (аліас)."""
        return self.format_public_report


__all__ = ["ColorSizeFormatter"]
