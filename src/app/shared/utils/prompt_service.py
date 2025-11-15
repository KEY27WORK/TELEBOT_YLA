# 🧾 app/shared/utils/prompt_service.py
"""
🧾 Сервіс для роботи з текстовими шаблонами і OCR-промптами.

🔹 Ледаче завантаження з кешем та зрозумілими помилками.
🔹 Форматує шаблони з параметрами, захищаючи від пропущених плейсхолдерів.
🔹 Комбінує текст та JSON-приклади для генерації OCR-запитів.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import json                                              # 📦 Обробка JSON-прикладів
import logging                                           # 🪵 Логування подій сервісу
from enum import Enum                                    # 🧮 Переліки типів
from functools import lru_cache                          # 💾 Кешування завантажень
from pathlib import Path                                 # 📂 Операції з файловими шляхами
from typing import Dict, Optional                        # 🧰 Типи аргументів

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME             # 🏷️ Базове імʼя логера

logger = logging.getLogger(f"{LOG_NAME}.prompts")        # 🧾 Іменований логер сервісу


# ================================
# 🧮 ТИПИ ШАБЛОНІВ
# ================================
class PromptType(str, Enum):
    """Перелік доступних текстових шаблонів."""

    MUSIC = "music"                                      # 🎵 Промпти для музичних описів
    HASHTAGS = "hashtags"                                # 🏷️ Генерація хештегів
    WEIGHT = "weight"                                    # ⚖️ Оцінка ваги товару
    CLOTHING_TYPE = "clothing_type"                      # 👗 Визначення типу одягу
    TRANSLATION = "translation"                          # 🌐 Переклад текстів
    SLOGAN = "slogan"                                    # ✨ Рекламні слогани


class ChartType(str, Enum):
    """Типи розмірних таблиць для OCR-промптів."""

    GENERAL = "general"                                  # 📊 Загальний шаблон
    UNIQUE = "unique"                                    # 🧬 Унікальна таблиця
    UNIQUE_GRID = "unique_grid"                          # 🗂️ Таблиця з сіткою


# ================================
# 🧾 СЕРВІС ШАБЛОНІВ
# ================================
class PromptService:
    """Ледачий та безпечний сервіс для текстових шаблонів і OCR-активів."""

    def __init__(self, prompts_root: Optional[Path] = None, lang: str = "uk") -> None:
        """Налаштовує кореневий каталог шаблонів та мову за замовчуванням."""
        self._root = prompts_root or (Path(__file__).parent.parent / "prompts")  # 📂 База шаблонів
        self._lang = lang                                                        # 🌐 Обрана мова

    # ================================
    # 🚀 ПУБЛІЧНИЙ API
    # ================================
    def get_prompt(self, prompt_type: PromptType, **kwargs: Dict[str, object]) -> str:
        """Повертає відформатований шаблон для заданого типу."""
        template = self._load_lang_text(f"{prompt_type.value}.txt", lang=self._lang)  # 📄 Дістаємо шаблон
        safe_kwargs = {key: ("" if value is None else value) for key, value in kwargs.items()}  # 🛡️ Заміна None
        try:
            return template.format(**safe_kwargs)                                  # 🧵 Форматуємо шаблон
        except KeyError as error:                                                  # ⚠️ Відсутній плейсхолдер
            missing = error.args[0]                                                # 🔎 Назва плейсхолдеру
            raise ValueError(
                f"Missing placeholder '{missing}' for prompt '{prompt_type.value}.txt'"
            ) from error                                                           # 🚨 Пояснення помилки

    def get_size_chart_prompt(self, chart_type: ChartType) -> str:
        """Комбінує текстовий шаблон та JSON-приклад для OCR."""
        base_template = self._load_ocr_file("base.txt")                            # 📄 Базовий текст OCR
        example_name = f"example_{chart_type.value}.json"                          # 🧾 Назва JSON-файлу
        try:
            example_raw = self._load_ocr_file(example_name)                        # 📄 Завантажуємо JSON-приклад
        except FileNotFoundError as error:                                         # ⚠️ Приклад відсутній
            raise ValueError(f"OCR example file not found: {example_name}") from error

        example = json.loads(example_raw)                                          # 📦 Десеріалізуємо JSON
        conditions = {
            ChartType.UNIQUE: "Поверни лише JSON і нічого більше...",              # 🧾 Специфіка для унікальних таблиць
            ChartType.GENERAL: "Поверни JSON з масивами значень...",               # 🧾 Вимоги для загальної таблиці
        }
        prompt = base_template.format(
            extra_conditions=conditions.get(chart_type, ""),                       # 🧰 Додаємо додаткові умови
            example_json=json.dumps(example, indent=4, ensure_ascii=False),        # 📄 Форматуємо приклад
        )
        return prompt                                                              # 📬 Повертаємо зібраний промпт

    def load_text(self, fname: str, *, lang: Optional[str] = None) -> str:
        """Повертає сирий текст шаблону без форматування."""
        target_lang = lang or self._lang                                           # 🌐 Перевага аргументу
        return self._load_lang_text(fname, lang=target_lang)                       # 📄 Повертаємо текст

    # ================================
    # 🛠️ ПРИВАТНІ ЗАВАНТАЖУВАЧІ
    # ================================
    @lru_cache
    def _load_lang_text(self, fname: str, *, lang: str) -> str:
        """Ледаче завантаження мовного шаблону з кешуванням."""
        prompt_path = self._root / lang / fname                                    # 📂 Формуємо шлях
        try:
            with open(prompt_path, "r", encoding="utf-8") as handle:
                text = handle.read()                                               # 📖 Зчитуємо файл
            logger.debug("📄 Зчитано файл шаблону: %s", prompt_path)               # 🪵 Лог успіху
            return text                                                            # 📬 Повертаємо текст
        except FileNotFoundError as error:                                         # ⚠️ Шаблон відсутній
            logger.error("❌ Файл шаблону не знайдено: %s", prompt_path)           # 🪵 Лог помилки
            raise error                                                            # 🚨 Пробросимо виняток далі

    @lru_cache
    def _load_ocr_file(self, fname: str) -> str:
        """Завантажує OCR-файли з підкаталогу `ocr`."""
        asset_path = self._root / "ocr" / fname                                    # 📂 Шлях до OCR-файлу
        try:
            with open(asset_path, "r", encoding="utf-8") as handle:
                text = handle.read()                                               # 📖 Зчитуємо файл
            logger.debug("📄 Зчитано OCR-актив: %s", asset_path)                   # 🪵 Лог успіху
            return text                                                            # 📬 Повертаємо вміст
        except FileNotFoundError as error:                                         # ⚠️ OCR-актив відсутній
            logger.error("❌ OCR-актив не знайдено: %s", asset_path)               # 🪵 Лог помилки
            raise error                                                            # 🚨 Пробросимо виняток
