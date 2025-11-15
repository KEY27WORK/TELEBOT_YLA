# 🎨 app/bot/ui/formatters/message_formatter.py
"""
🎨 Форматує дані товару у безпечний HTML-блок для Telegram.

🔹 Очищує текстові секції та заголовки від небезпечних символів
🔹 Розпізнає, коли всі варіанти позначені як «❌» (SOLD OUT)
🔹 Будує health-блок з індикаторами наявності ресурсів
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (відсутні)

# 🔠 Системні імпорти
from dataclasses import asdict                                      # 🧱 Перетворення dataclass у dict
from html import escape                                             # 🧼 Екранування HTML-символів
from typing import Any, Final                                       # 🧰 Типізація та константи

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.content.product_content_service import (    # 📦 DTO з підготовленими даними товару
    ProductContentDTO,
)

# ================================
# 🔧 КОНСТАНТИ МОДУЛЯ
# ================================
_LBL_MATERIAL: Final[str] = "МАТЕРІАЛ"                              # 🏷️ Рядок заголовку секції «Матеріал»
_LBL_FIT: Final[str] = "ПОСАДКА"                                    # 🏷️ Рядок заголовку секції «Посадка»
_LBL_DESC: Final[str] = "ОПИС"                                      # 🏷️ Рядок заголовку секції «Опис»
_LBL_MODEL: Final[str] = "МОДЕЛЬ"                                   # 🏷️ Рядок заголовку секції «Модель»
_MAX_SECTION_LEN: Final[int] = 2_000                                # 📏 Ліміт символів для довільних секцій
_MAX_TITLE_LEN: Final[int] = 256                                    # 📏 Ліміт символів для заголовку товару


# ================================
# 🖼️ ФОРМАТУВАЛЬНИК ПОВІДОМЛЕНЬ
# ================================
class MessageFormatter:
    """
    📦 Відповідає за формування HTML-повідомлень (parse_mode='HTML') без бізнес-логіки.
    """

    # ================================
    # 🧾 ЛОГІКА SOLD OUT
    # ================================
    @staticmethod
    def is_fully_sold_out(colors_text: str) -> bool:
        """
        Визначає, чи містить блок кольорів лише позначки «❌».

        Args:
            colors_text: Сирий текстовий блок з варіантами кольорів/розмірів.

        Returns:
            True, якщо кожен непорожній рядок містить «❌».
        """
        if not colors_text or not colors_text.strip():               # 🟡 Порожній блок не рахуємо як розпроданий
            return False
        lines = [ln for ln in colors_text.splitlines() if ln.strip()]  # 📋 Витягуємо непорожні рядки
        return bool(lines) and all("❌" in ln for ln in lines)        # ✅ Усі рядки мають маркер «❌»

    # ================================
    # 🧼 САНІТИЗАЦІЯ ТЕКСТУ
    # ================================
    @staticmethod
    def _sanitize_text(value: str | None, *, max_len: int = _MAX_SECTION_LEN) -> str:
        """
        Повертає безпечний текст: trim + обрізання + HTML-escape.
        """
        if not value:                                                # 🟡 Порожні значення замінюємо плейсхолдером
            return "Немає даних"
        trimmed = value.strip()                                      # ✂️ Прибираємо пробіли на краях
        if len(trimmed) > max_len:                                   # 📏 Перевіряємо довжину
            trimmed = trimmed[: max_len - 1] + "…"                   # ✂️ М'яко обрізаємо та додаємо «…»
        return escape(trimmed, quote=True)                           # 🧼 Екрануємо HTML-символи

    @staticmethod
    def _sanitize_title(title: str | None) -> str:
        """
        Очищує заголовок та приводить його до верхнього регістру.
        """
        safe = MessageFormatter._sanitize_text(title, max_len=_MAX_TITLE_LEN)  # 🧼 Заголовок із лімітом
        return safe.upper()                                         # 🔠 Приводимо до верхнього регістру

    # ================================
    # ✍️ ГОЛОВНИЙ ФОРМАТЕР ОПИСУ
    # ================================
    @staticmethod
    def format_description(data: ProductContentDTO) -> str:
        """
        Формує повний HTML-блок опису товару з урахуванням SOLD OUT та health-блоків.
        """
        material = MessageFormatter._sanitize_text(data.sections.get(_LBL_MATERIAL))   # 🧵 Секція «Матеріал»
        fit = MessageFormatter._sanitize_text(data.sections.get(_LBL_FIT))             # 🧍 Секція «Посадка»
        description = MessageFormatter._sanitize_text(data.sections.get(_LBL_DESC))    # 📄 Секція «Опис»
        model = MessageFormatter._sanitize_text(data.sections.get(_LBL_MODEL))         # 🧑‍🎤 Секція «Модель»
        colors_block = MessageFormatter._sanitize_text(data.colors_text)               # 🎨 Блок кольорів/розмірів

        title_safe = MessageFormatter._sanitize_title(data.title)                      # 🏷️ Підготовлений заголовок
        is_sold_out = MessageFormatter.is_fully_sold_out(data.colors_text or "")       # 🚦 Перевіряємо SOLD OUT
        title_display = (                                                             # 🧾 Формуємо відображення заголовку
            f"❌ РОЗПРОДАНО ❌\\n\\n{title_safe}" if is_sold_out else title_safe
        )

        slogan_safe = MessageFormatter._sanitize_text(data.slogan)                     # ✨ Слоган
        hashtags_safe = MessageFormatter._sanitize_text(data.hashtags)                 # #️⃣ Хештеги

        formatted = (                                                                  # 🏗️ Конструюємо HTML
            f"<b>{title_display}:</b>\n\n"
            f"<b>{_LBL_MATERIAL}:</b> {material}\n"
            f"<b>{_LBL_FIT}:</b> {fit}\n"
            f"<b>{_LBL_DESC}:</b> {description}\n\n"
            f"{colors_block}\n\n"
            f"<b>{_LBL_MODEL}:</b> {model}\n\n"
            f"<b>{slogan_safe}</b>\n\n"
            f"<b>{hashtags_safe}</b>"
        )
        return formatted                                             # 📤 Повертаємо готовий HTML

    # ================================
    # 🩺 HEALTH-БЛОК
    # ================================
    @staticmethod
    def format_health(diagnostics: Any | None) -> str:
        """
        Повертає компактний health-блок або порожній рядок, якщо дані відсутні.
        """
        if diagnostics is None:                                      # 🟡 Немає діагностики — повертаємо порожній рядок
            return ""
        try:
            source = (                                               # 🔄 Об'єднуємо dataclass та dict
                asdict(diagnostics) if hasattr(diagnostics, "__dataclass_fields__") else dict(diagnostics)
            )
        except Exception:
            return ""                                                # 🛡️ Некоректний формат — тихо ігноруємо

        images_count = int(source.get("images_count", 0) or 0)       # 🖼 Кількість зображень
        has_size_chart = bool(source.get("has_size_chart", False))   # 📏 Наявність size-chart
        ocr_status = str(source.get("ocr_status", "") or "").lower() # 🔡 Статус OCR у нижньому регістрі

        size_chart_tag = "📏 SC" if has_size_chart else "📏 —"        # 🧾 Індикація size-chart
        ocr_map = {                                                  # 🗺️ Мапа статусів OCR → бейджів
            "ok": "🟢 OK",
            "not_found": "⚪️ —",
            "failed": "🔴 FAIL",
            "not_run": "⚪️ —",
        }
        ocr_tag = ocr_map.get(ocr_status, f"⚪️ {ocr_status or '—'}") # 🧾 Обираємо бейдж (або дефолт)

        return f"— — —\\n🖼 {images_count} | {size_chart_tag} | 🔎 OCR: {ocr_tag}"  # 📤 Health-блок
