""" music_recommendation.py — Оптимизированный модуль для подбора музыки.

🔹 Класс `MusicRecommendation`:
  - Использует OpenAI GPT-4 для генерации списка песен.
  - Анализирует название, описание и изображение товара.
  - Поддерживает Singleton (один объект на весь процесс).
  - Логирует процесс генерации и ошибки.

📌 Использует:
  - `ConfigService` для загрузки API-ключа.
"""

import logging
import asyncio
from utils.prompt_service import PromptService
from errors.error_handler import error_handler
from services.open_ai_serv import OpenAIService


class MusicRecommendation:
    """
    Класс для генерации музыкальных рекомендаций на основе описания товара.
    """

    def __init__(self):
        self.openai_service = OpenAIService()

    def find_music(self, title: str, description: str, image_url: str) -> str:
        """
        Ищет подходящую музыку для товара.

        :param title: Название товара.
        :param description: Описание товара.
        :param image_url: Ссылка на изображение товара.
        :return: Название песни или сообщение об ошибке.
        """
        logging.info(f"🎵 Подбор музыки для: {title}")

        prompt = PromptService.get_music_prompt(title, description, image_url)
        song_response = self.openai_service.chat_completion(prompt, temperature=0.7)
        if song_response != "ERROR":
            logging.info(f"🎶  Рекомендованные треки: \n {song_response}")
            return song_response
        else:
            return "Музыка не была подобрана!"
            

# 🔹 Пример использования:
if __name__ == "__main__":
    music_service = MusicRecommendation()
    result = music_service.find_music(
        title="W621 Headband Trio",
        description="Эластичная и удобная повязка на голову для спорта.",
        image_url="https://example.com/image.jpg"
    )
    print(result)
