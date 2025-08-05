# 🧠 app/shared/utils/prompt_service.py
"""
🧠 prompt_service.py — сервіс для генерації промтів для OpenAI.

🔹 Клас `PromptService`:
- Інкапсулює логіку створення всіх типів промтів.
- Інтегрований з централізованою системою логування.
- Використовує шаблони з `prompts.py`.
"""

# 🔠 Системні імпорти
import logging														                                    # 🧾 Вбудований модуль для логування

# 🧠 Інтерфейс
from app.domain.ai.interfaces.prompt_service_interface import IPromptService                            # 📎 Абстрактний інтерфейс

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME						                                    # 🪪 Базова назва логера
from app.shared.utils.prompts import (                                                                  # 🧠 Генератори шаблонів промтів
    get_prompt,
    get_size_chart_prompt,
    PromptType,
    ChartType
    )                              

# ================================
# 🧾 ІНІЦІАЛІЗАЦІЯ ЛОГЕРА
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai")


# ================================
# 🏛️ КЛАС СЕРВІСУ ПРОМТІВ
# ================================

class PromptService(IPromptService):
    """
    🔧 Сервіс, що відповідає за створення та форматування промтів для OpenAI.
    """

    def __repr__(self) -> str:
        """
        🎛️ Повертає представлення об'єкта для відладки.
        """
        return f"<PromptService id={id(self)}>"

    def _log_prompt(self, prompt_name: str, prompt_text: str, context: str):
        """
        🧾 Приватний метод для логування згенерованого промта.
        """
        logger.debug(f"Створення промта '{prompt_name}' для: {context}")                                                # 🧠 Назва промта й контекст
        logger.debug(f"📤 Згенерований промт (початок): {prompt_text[:300]}...")                                        # 🔎 Обрізаємо довгий текст

    def get_slogan_prompt(self, title: str, description: str) -> str:
        """🎯 Генерує промт для створення слогану."""
        prompt = get_prompt(PromptType.SLOGAN, title=title, description=description)                             # 🧩 Підставляємо значення
        self._log_prompt("slogan", prompt, title)                                                                       # 🧾 Логування
        return prompt

    def get_music_prompt(self, description: str) -> str:
        """🎵 Генерує промт для підбору музичних рекомендацій."""
        prompt = get_prompt(PromptType.MUSIC, description=description)                                          # 🎶 Промт по опису
        self._log_prompt("music", prompt, description)                                                                  # 🧾 Логування
        return prompt

    def get_translation_prompt(self, text: str) -> str:
        """🌍 Генерує промт для перекладу тексту."""
        prompt = get_prompt(PromptType.TRANSLATION, text=text)                                                                     # 🌐 Шаблон без підстановки
        self._log_prompt("translation", prompt, f"текст довжиною {len(text)}")                                          # 🧾 Логуємо довжину
        return prompt

    def get_weight_prompt(self, title: str, description: str, image_url: str) -> str:
        """⚖️ Генерує промт для оцінки ваги товару."""                                          
        prompt = get_prompt(PromptType.WEIGHT, title=title, description=description, image_url=image_url)            # ⚖️ Дані + зображення
        self._log_prompt("weight", prompt, title)
        return prompt

    def get_clothing_type_prompt(self, title: str) -> str:
        """🧥 Генерує промт для визначення типу одягу."""
        prompt = get_prompt(PromptType.CLOTHING_TYPE, title=title)                                                        # 👕 Промт з назвою
        self._log_prompt("clothing_type", prompt, title)
        return prompt

    def get_hashtags_prompt(self, title: str, description: str) -> str:
        """#️⃣ Генерує промт для створення хештегів."""
        prompt = get_prompt(PromptType.HASHTAGS, title=title, description=description)                                       # 🏷️ Опис → хештеги
        self._log_prompt("hashtags", prompt, title)
        return prompt

    def get_size_chart_prompt(self, chart_type: ChartType) -> str:
        """📏 Генерує промт для обробки таблиці розмірів."""
        prompt = get_size_chart_prompt(chart_type)                                                                      # 📐 Тип таблиці
        self._log_prompt("size_chart", prompt, chart_type)
        return prompt
