# 🎵 app/infrastructure/music/music_recommendation.py
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
from app.infrastructure.ai.prompt_service import PromptService
from app.errors.error_handler import error_handler
from app.infrastructure.ai.open_ai_serv import OpenAIService
from app.config.config_service import ConfigService


class MusicRecommendation:
    """🎧 Генератор музичних рекомендацій на основі опису товару.

    🔹 Логіка:
    - Формує промпт через PromptService
    - Надсилає запит до OpenAI GPT-4
    - Повертає результат або повідомлення про помилку
    """

    def __init__(self, openai_service: OpenAIService):
        """
        🔧 Ініціалізація з впровадженням залежності OpenAIService.
        """
        self.openai_service = openai_service
        logging.info("✅ MusicRecommendation успішно ініціалізовано.")

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
        prompt = PromptService.get_music_prompt(title, description, image_url)
        
        # ✅ Використовуємо asyncio.to_thread для запуску синхронного коду в асинхронному потоці
        song_response = await asyncio.to_thread(
            self.openai_service.chat_completion, prompt, temperature=0.7
        )

        if "ERROR" not in song_response:
            logging.info(f"🎶 Рекомендовані треки:\n{song_response}")
            return song_response

        logging.warning("⚠️ Не вдалося підібрати музику через OpenAI.")
        return "Музика не була підібрана!"


# 🔹 Приклад локального запуску
if __name__ == "__main__":
    config_serv = ConfigService()
    open_ai_serv = OpenAIService(config_service=config_serv)
    music_service = MusicRecommendation(open_ai_serv)
    result = music_service.find_music(
        title="W621 Headband Trio",
        description="Еластична і зручна пов'язка на голову для спорту.",
        image_url="https://example.com/image.jpg"
    )
    print(result)