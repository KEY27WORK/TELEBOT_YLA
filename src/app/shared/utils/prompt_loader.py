# ⚙️ app/shared/utils/prompt_loader.py
"""
⚙️ prompt_loader.py — завантажує та кешує текстові шаблони промтів з файлів.
"""

# 🔠 Системні імпорти
import logging																    # 🧾 Логування
from pathlib import Path														# 📁 Шлях до файлів
from functools import lru_cache											        # 🧠 Кешування результатів

# 🧹 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME							        # 🚫 Ім'я централізованого логера

logger = logging.getLogger(LOG_NAME)										    # 🧾 Ініціалізуємо логер

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"			                # 📁 Базова директорія шаблонів

# ================================
# 🌀 ФУНКЦІЯ: ЗАВАНТАЖЕННЯ ШАБЛОНУ
# ================================

@lru_cache
def load_prompt(file_name: str, lang: str = "uk") -> str:
    """
    📅 Завантажує текст промта з мовної директорії (/prompts/uk/).
    """
    file_path = _PROMPTS_DIR / lang / file_name									# 📁 Формуємо шлях до файлу
    try:
        logger.debug(f"Завантаження промта з файлу: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:						# 📖 Читаємо файл
            return f.read()
    except FileNotFoundError:
        logger.error(f"❌ Файл промта не знайдено: {file_path}")
        raise

# ================================
# 🏢 ФУНКЦІЯ: ЗАВАНТАЖЕННЯ OCR-АССЕТІВ
# ================================

@lru_cache
def load_ocr_asset(file_name: str) -> str:
    """
    📅 Завантажує OCR-ассет (JSON приклад або шаблон).
    """
    file_path = _PROMPTS_DIR / "ocr" / file_name								# 🧾 OCR-директорія
    try:
        logger.debug(f"Завантаження OCR ассету з файлу: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:						# 📖 Читаємо OCR-файл
            return f.read()
    except FileNotFoundError:
        logger.error(f"❌ OCR ассет не знайдено: {file_path}")
        raise
