""" 🧠 open_ai_serv.py — сервіс роботи з OpenAI API.

🔹 Клас `OpenAIService`:
- Використовується для запитів до GPT-4 Turbo (chat_completion).
- Підтримує кастомну температуру (temperature).
- Має обробку помилок, включно з RateLimitError.

Використовує:
- OpenAI SDK (openai-python)
- Логування через стандартний logging
- Singleton-конфігурацію з ConfigService
"""

# 🔍 OpenAI API
import openai
from openai import RateLimitError

# ⚙️ Залежності
import logging
from core.config.config_service import ConfigService


class OpenAIService:
    """ 🧠 Сервіс для взаємодії з OpenAI (GPT-4 Turbo).
    
    Використовується:
    - TranslatorService
    - PromptService (не напряму, але через клас)
    - HashtagGenerator
    """

    def __init__(self):
        self.config = ConfigService()  # 🧱 Singleton-конфігурація
        self.client = openai.OpenAI(api_key=self.config.openai_api_key)  # 🔑 Ініціалізація клієнта

    def chat_completion(self, prompt: str, temperature: float = 0.3) -> str:
        """ 📩 Надсилає промт до GPT-4 Turbo і повертає текст відповіді.

        :param prompt: Створений текстовий запит.
        :param temperature: Креативність відповіді (0.0 – фактологічно точно, 1.0 – креативно).
        :return: Стрічка з відповіддю або "ERROR" у разі невдачі.
        """
        try:
            logging.info("📤 Надсилання запиту до GPT-4")
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            result = response.choices[0].message.content.strip()
            logging.info("✅ Отримано відповідь від OpenAI")
            return result

        except RateLimitError:
            logging.error("❌ Перевищено ліміт запитів OpenAI (RateLimitError)")
            return "ERROR: RateLimitError"

        except Exception as e:
            logging.error(f"❌ Невідома помилка OpenAI: {e}")
            return "ERROR"

        