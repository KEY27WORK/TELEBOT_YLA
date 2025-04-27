""" 🏷️ hashtag_generator.py — генерація хештегів для товарів YoungLA.

🔹 Клас:
- `HashtagGenerator` — створює релевантні хештеги:
    - базові #younglaukraine, #одяг тощо
    - AI-хештеги (через GPT-4)
    - гендерні (на основі артикула)
    - тип одягу (через AI)

Використовує:
- GPT-4 через OpenAI API
- PromptService для генерації промптів
"""

# 🧠 AI та OpenAI
import openai
import asyncio

# ⚙️ Системні
import os
import re
import logging

# 🧩 Зовнішні сервіси
from core.config.config_service import ConfigService
from utils.prompt_service import PromptService


class HashtagGenerator:
    """ 🏷️ Генератор хештегів для товарів YoungLA.

    ✔️ Використовує GPT-4 для підбору хештегів на основі опису.
    ✔️ Додає базові, гендерні, та AI-хештеги.
    """

    BASE_HASHTAGS = [
        "#YoungLA", "#younglaukraine", "#yla",
        "#одяг", "#одягукраїна", "#одягкиїв"
    ]

    def __init__(self):
        """🔧 Ініціалізує сервіс GPT-4 і завантажує конфіг."""
        self.config = ConfigService()
        self.client = openai.OpenAI()

    async def generate(self, title: str, description: str) -> str:
        """ 🧠 Генерує релевантні хештеги для товару.

        :param title: Назва товару (наприклад, "W214 Oversized Tee")
        :param description: Опис товару
        :return: Строка з унікальними хештегами
        """
        logging.info("🔍 Генерація хештегів для товару")

        hashtags = self.BASE_HASHTAGS.copy()

        # 🔠 Визначаємо артикул і гендерні теги
        article = self.extract_article(title)
        hashtags.extend(self.get_gender_hashtags(article))

        # 🤖 Паралельно визначаємо тип одягу та AI-хештеги
        clothing_task = asyncio.to_thread(self.extract_clothing_type, title)
        ai_task = asyncio.to_thread(self.generate_ai_hashtags, title, description)
        clothing_type, ai_hashtags = await asyncio.gather(clothing_task, ai_task)

        if clothing_type:
            hashtags.append(f"#{clothing_type.replace(' ', '').lower()}")

        hashtags.extend(ai_hashtags)

        return " ".join(sorted(set(hashtags)))

    def extract_article(self, title: str) -> str:
        """ 🔢 Витягує артикул товару з назви.
        """
        match = re.match(r"^([A-Za-z0-9]+)", title)
        return match.group(1) if match else ""

    def get_gender_hashtags(self, article: str) -> list:
        """ 🚻 Повертає хештеги за статтю на основі артикула.
        """
        if article.startswith("W"):
            logging.info("👩‍🦰 Жіночі хештеги")
            return ["#одягдлядівчат", "#одягдлянеї", "#жіночийодяг", "#younglaforher"]

        logging.info("👨‍🦱 Чоловічі хештеги")
        return ["#чоловічийодягукраїна", "#одягдлячоловіків"]

    def extract_clothing_type(self, title: str) -> str:
        """ 👕 Визначає тип одягу через GPT-4.
        """
        prompt = PromptService.get_clothing_type_prompt(title)
        logging.info(f"🤖 AI визначення типу одягу для: {title}")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content.strip().lower()
        except Exception as e:
            logging.error(f"❌ Помилка AI для типу одягу: {e}")
            return ""

    def generate_ai_hashtags(self, title: str, description: str) -> list[str]:
        """ 🧠 Використовує GPT-4 для генерації додаткових хештегів.
        """
        prompt = PromptService.get_hashtags_prompt(title, description)
        logging.info("🎯 AI запит на хештеги")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content.strip().split()
        except Exception as e:
            logging.error(f"❌ Помилка AI-хештегів: {e}")
            return ["#ошибка", "#хэштеги", "#недоступно"]
