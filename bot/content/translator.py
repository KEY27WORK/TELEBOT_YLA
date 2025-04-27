""" 🌐 translator.py — модуль для роботи з OpenAI GPT-4.

🔹 Клас:
- `TranslatorService` — переклад тексту, генерація слоганів та оцінка ваги товару.

Використовує:
- OpenAI GPT-4 через `OpenAIService`
- `PromptService` для генерації промптів
- Логування для діагностики та відладки
"""

# 🧠 GPT-4 API
from services.open_ai_serv import OpenAIService
from utils.prompt_service import PromptService

# 🧱 Системні
import logging


class TranslatorService:
    """ 🌐 Сервіс перекладу, генерації слоганів та оцінки ваги товару.

    ✔️ Переклад опису на українську
    ✔️ Генерація слогану
    ✔️ AI-оцінка ваги на основі зображення та опису
    """

    def __init__(self):
        """🔧 Ініціалізація OpenAI-сервісу."""
        self.openai_service = OpenAIService()

    def get_weight_estimate(self, title: str, description: str, image_url: str) -> float:
        """ ⚖️ Оцінює вагу товару на основі назви, опису та зображення.

        :param title: Назва товару
        :param description: Опис товару
        :param image_url: Посилання на зображення
        :return: Вага в кг (float)
        """
        logging.info(f"⚖️ Запит на оцінку ваги: {title}")
        prompt = PromptService.get_weight_prompt(title, description, image_url)
        response = self.openai_service.chat_completion(prompt, temperature=0.3)

        try:
            weight = float(response)
            weight = max(0.1, min(weight, 5.0))  # Обмеження: 0.1 – 5.0 кг
            logging.info(f"✅ Визначена вага: {weight} кг")
            return weight
        except ValueError:
            logging.error("❌ Неможливо визначити вагу. Використовується стандартне значення 1.0 кг.")
            return 1.0

    def translate_text(self, text: str) -> dict:
        """
        🌍 Перекладає текст на українську і структурує його за категоріями.

        :param text: Оригінальний опис
        :return: Словник категорій: МАТЕРІАЛ, ПОСАДКА, ОПИС, МОДЕЛЬ
        """
        logging.info("🌍 Запит на переклад і структурування тексту")
        prompt = PromptService.get_translation_prompt(text)
        response = self.openai_service.chat_completion(prompt + f"\n\n{text}")

        # 🔠 Парсимо відповідь у структуру
        sections = {"МАТЕРІАЛ": "", "ПОСАДКА": "", "ОПИС": "", "МОДЕЛЬ": ""}
        current_section = None

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("МАТЕРІАЛ"):
                current_section = "МАТЕРІАЛ"
            elif line.startswith("ПОСАДКА"):
                current_section = "ПОСАДКА"
            elif line.startswith("ОПИС"):
                current_section = "ОПИС"
            elif line.startswith("МОДЕЛЬ"):
                current_section = "МОДЕЛЬ"
            if current_section:
                content = line.replace(f"{current_section}:", "").strip()
                sections[current_section] += content + " "

        result = {key: value.strip() for key, value in sections.items() if value.strip()}
        logging.info("✅ Переклад успішно виконано")
        return result

    def generate_slogan(self, title: str, description: str) -> str:
        """
        🎯 Генерує короткий слоган до 10 слів українською.

        :param title: Назва товару
        :param description: Опис товару
        :return: Слоган
        """
        logging.info(f"🎯 Генерація слогану для: {title}")
        prompt = PromptService.get_slogan_prompt(title, description)
        response = self.openai_service.chat_completion(prompt, temperature=0.7)

        if response != "ERROR":
            logging.info(f"✅ Слоган успішно згенеровано: {response}")
            return response
        else:
            return "Стильний вибір для вашого гардеробу! 🚀"
