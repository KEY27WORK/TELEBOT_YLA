# 🤖 app/infrastructure/ai/translator.py
"""
🤖 translator.py — сервіс для перекладу та генерації тексту через OpenAI.

Використовує:
- OpenAIService — для виконання запитів
- PromptService — для формування текстових запитів (prompt templates)
"""

# 🔠 Системные импорты
import logging                                                                         # 🧾 Логування
from enum import Enum                                                                   # 🏷️ Для створення перелічень (уніфікація ключів)
from typing import Dict, Optional                                                       # 🧩 Типізація

# 🧩 Внутренние модули проекта
from .open_ai_serv import OpenAIService                                                 # 🧠 Основний сервіс для роботи з GPT
from app.infrastructure.ai.prompt_service import PromptService                          # 📝 Генератор промтів
from app.shared.utils.logger import LOG_NAME							            	# 🪪 Базове імʼя логера


# ================================
# 🧾 ІНІЦІАЛІЗАЦІЯ ЛОГЕРА
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai")

# ================================
# 🏷️ КОНСТАНТИ ТА ENUM'И
# ================================
class SectionKey(str, Enum):
    MATERIAL = "МАТЕРІАЛ"
    FIT = "ПОСАДКА"
    DESCRIPTION = "ОПИС"
    MODEL = "МОДЕЛЬ"

DEFAULT_SLOGAN = "Стильний вибір для вашого гардеробу! 🚀"

# ================================
# 🏛️ КЛАС СЕРВІСУ-ПЕРЕКЛАДАЧА
# ================================
class TranslatorService:
    """
    🌐 Сервіс, що виконує конкретні завдання з обробки тексту,
    використовуючи загальний `OpenAIService`.
    """

    def __init__(self, openai_service: OpenAIService, prompt_service: PromptService):
        """
        ⚙️ Ініціалізація сервісу з впровадженням залежностей.
        """
        self.openai_service = openai_service
        self.prompt_service = prompt_service  # ✅ Зберігаємо екземпляр сервісу
        logger.info("✅ TranslatorService успішно ініціалізовано.")

    # ================================
    # ⚖️ ОЦІНКА ВАГИ
    # ================================
    async def get_weight_estimate(self, title: str, description: str, image_url: str) -> float:
        """
        ⚖️ Оцінює вагу товару на основі назви, опису та зображення.
        """
        logger.info(f"⚖️ Запит на оцінку ваги для: {title}")
        prompt = self.prompt_service.get_weight_prompt(title, description, image_url)
        response = await self.openai_service.chat_completion(prompt, temperature=0.3)

        if response is None:
            logger.error("❌ Отримана порожня відповідь (None) від OpenAI для оцінки ваги. Використовується стандартне значення 1.0 кг.")
            return 1.0

        try:
            weight = float(response)
            clamped_weight = max(0.1, min(weight, 5.0))
            logger.info(f"✅ Визначена вага: {clamped_weight} кг")
            return clamped_weight
        except (ValueError, TypeError):
            logger.error(f"❌ Неможливо розпізнати вагу з відповіді '{response}'. Використовується стандартне значення 1.0 кг.")
            return 1.0

    # ================================
    # 📜 ПЕРЕКЛАД ТА СТРУКТУРУВАННЯ
    # ================================
    async def translate_text(self, text: str) -> dict[str, str]:
        """
        🌍 Перекладає текст на українську і структурує його за категоріями.
        """
        logger.info("🌍 Запит на переклад і структурування тексту...")
        prompt = self.prompt_service.get_translation_prompt(text)
        response = await self.openai_service.chat_completion(prompt + f"\n\n{text}")
        
        if not response:
            logger.warning("Отримана порожня відповідь від OpenAI для перекладу. Повертаю порожній результат.")
            return {}
        
        return self._parse_translated_sections(response)

    def _parse_translated_sections(self, response_text: str) -> dict[str, str]:
        """
        🧩 Парсить текстову відповідь від OpenAI у структурований словник.
        """
        sections = {key.value: "" for key in SectionKey}
        current_section: Optional[SectionKey] = None

        for line in response_text.split("\n"):
            line = line.strip()
            for key in SectionKey:
                if line.startswith(f"{key.value}:"):
                    current_section = key
                    break
            
            if current_section:
                content = line.replace(f"{current_section.value}:", "").strip()
                if content:
                    sections[current_section.value] += content + " "

        result = {key: value.strip() for key, value in sections.items() if value.strip()}
        logger.info("✅ Переклад успішно розпарсено.")
        return result

    # ================================
    # 🎯 ГЕНЕРАЦІЯ СЛОГАНУ
    # ================================
    async def generate_slogan(self, title: str, description: str) -> str:
        """
        🎯 Генерує короткий слоган до 10 слів українською.
        """
        logger.info(f"🎯 Генерація слогану для: {title}")
        prompt = self.prompt_service.get_slogan_prompt(title, description)
        response = await self.openai_service.chat_completion(prompt, temperature=0.7)

        if not isinstance(response, str) or "ERROR" in response:
            logger.warning("⚠️ Помилка генерації слогану або некоректна відповідь.")
            return DEFAULT_SLOGAN

        logger.info(f"✅ Слоган успішно згенеровано: {response}")
        return response
