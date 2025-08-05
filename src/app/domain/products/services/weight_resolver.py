# ⚖️ app/domain/products/services/weight_resolver.py
"""
⚖️ weight_resolver.py — Сервіс для визначення ваги товару.

🔹 WeightResolver:
- Спочатку намагається знайти вагу в локальному словнику (через WeightDataService).
- Якщо не знайдено — викликає AI (через TranslatorService).
- Після цього оновлює кеш, щоб уникнути повторних викликів.
"""

# 🔠 Системні імпорти
import logging
from typing import Optional

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.data_storage.weight_data_service import WeightDataService 
from app.infrastructure.ai.translator import TranslatorService

class WeightResolver:
    """
    ⚖️ Розраховує вагу товару за назвою, описом і зображенням.
    Працює в два етапи: локально ➝ GPT fallback.
    """

    def __init__(self, weight_data_service: WeightDataService, translator_service: TranslatorService):
        """
        ⚙️ Ініціалізація з впровадженням правильних залежностей.
        """
        self.weight_data_service = weight_data_service
        self.translator_service = translator_service

    async def resolve(self, title: str, description: str, image_url: str) -> float:
        """
        🔍 Визначає вагу товару:
        1. Пошук за ключовим словом у назві в локальному словнику.
        2. Якщо не знайдено — GPT-оцінка на основі title/description/image.
        """
        title_lower = title.lower()
        weight_data = await self.weight_data_service.load()

        # 🧠 Крок 1. Пошук у словнику
        for keyword, weight in weight_data.items():
            if keyword in title_lower:
                logging.info(f"⚖️ Локальна вага знайдена: '{keyword}' = {weight} кг")
                return weight

        # 🤖 Крок 2. GPT fallback
        logging.info(f"🤖 Вага не знайдена в словнику. Викликаємо AI для: {title}")
        weight = await self.translator_service.get_weight_estimate(title, description, image_url)

        # 💾 Використовуємо новий сервіс для оновлення даних.
        await self.weight_data_service.update(title_lower, weight)

        return weight
