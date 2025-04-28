""" 🎵 music_recommendation.py — Оптимізований модуль для підбору музики до товарів.

🔹 Клас `MusicRecommendation`:
- Генерує музичні рекомендації за допомогою OpenAI GPT-4
- Аналізує назву, опис і зображення товару
- Працює як Singleton (один інстанс на весь процес)
- Логує процес генерації та помилки

📦 Використовує:
- OpenAIService — для запиту до GPT
- PromptService — для створення промпту
- ErrorHandler — для обробки помилок
"""

# 📦 Стандартні бібліотеки
import logging
import asyncio

# 🧠 Внутрішні сервіси
from utils.prompt_service import PromptService
from errors.error_handler import error_handler
from services.open_ai_serv import OpenAIService


class MusicRecommendation:
    """🎧 Генератор музичних рекомендацій на основі опису товару.

    🔹 Логіка:
    - Формує промпт через PromptService
    - Надсилає запит до OpenAI GPT-4
    - Повертає результат або повідомлення про помилку
    """

    def __init__(self):
        self.openai_service = OpenAIService()

    @error_handler
    async def find_music(self, title: str, description: str, image_url: str) -> str:
        """
        🎵 Підбирає музику на основі товару (асинхронно).

        :param title: Назва товару
        :param description: Опис товару
        :param image_url: Посилання на зображення
        :return: Рекомендовані треки або повідомлення про помилку
        """
        logging.info(f"🎼 Підбір музики для: {title}")

        # 🔹 Створення промпту
        prompt = PromptService.get_music_prompt(title, description, image_url)

        # 🤖 Виклик OpenAI через окремий потік
        song_response = await asyncio.to_thread(self.openai_service.chat_completion, prompt, temperature=0.7)

        # ✅ Якщо відповідь успішна — лог і повернення
        if song_response != "ERROR":
            logging.info(f"🎶 Рекомендовані треки:\n{song_response}")
            return song_response

        # ❌ В іншому випадку — повідомлення про помилку
        logging.warning("⚠️ Не вдалося підібрати музику через OpenAI.")
        return "Музыка не была подобрана!"


# 🔹 Приклад локального запуску
if __name__ == "__main__":
    music_service = MusicRecommendation()
    result = music_service.find_music(
        title="W621 Headband Trio",
        description="Еластична і зручна пов'язка на голову для спорту.",
        image_url="https://example.com/image.jpg"
    )
    print(result)
