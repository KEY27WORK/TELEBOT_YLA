""" 🧠 ocr_service.py — модуль OCR-розпізнавання таблиць розмірів через OpenAI Vision.

🔹 Клас:
- `OCRService` — виконує OCR-обробку зображень за допомогою GPT-4 Vision API.

📌 Використовує:
- `openai` — взаємодія з OpenAI API
- `base64` — кодування зображень
- `json`, `re` — обробка тексту
- `logging` — логування
- `PromptService` — отримання промтів

✅ Принципи SOLID:
- SRP — виконує тільки OCR
- DIP — не залежить від конкретної реалізації GPT
"""

# 🧱 Системні
import logging
import base64
import json
import re
from typing import Optional, Dict

# 🤖 OpenAI
import openai

# ⚙️ Промти
from utils.prompt_service import PromptService


class OCRService:
    """
    📷 Клас для OCR через OpenAI GPT-4 Vision API.

    Основна функція — перетворити зображення таблиці розмірів у структурований JSON.
    """

    def __init__(self, model: str = "gpt-4-turbo"):
        """
        Ініціалізація OCR-сервісу.

        :param model: Назва моделі OpenAI (за замовчуванням: gpt-4-turbo)
        """
        self.client = openai.OpenAI()
        self.model = model

    def recognize(self, image_path: str, size_chart_type: str) -> Optional[Dict]:
        """
        📥 Основний метод OCR-розпізнавання.

        :param image_path: Шлях до зображення.
        :param size_chart_type: Тип таблиці (уникальна / загальна).
        :return: Словник з розпізнаними даними або None.
        """
        logging.info(f"🔍 OCR запущено для: {image_path} | Тип: {size_chart_type}")

        try:
            # 📸 Читаємо та кодуємо зображення
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

            # 🧠 Готуємо промт
            prompt = PromptService.get_size_chart_prompt(size_chart_type)

            # 📤 Відправляємо запит до OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}
                        ]
                    }
                ],
                temperature=0.7
            )

            # 📦 Обробляємо результат
            raw_text = response.choices[0].message.content.strip()
            logging.info(f"✅ OCR-відповідь:\n{raw_text}")

            clean_text = self._clean_json_text(raw_text)
            return json.loads(clean_text)

        except (openai.OpenAIError, json.JSONDecodeError) as e:
            logging.error(f"❌ Помилка OCR: {e}")
            return None

    @staticmethod
    def _clean_json_text(json_text: str) -> str:
        """
        🧹 Очищає markdown (```) з JSON-відповіді.

        :param json_text: Текст з markdown-блоком
        :return: Чистий JSON як рядок
        """
        return re.sub(r"```json\n(.*?)\n```", r"\1", json_text, flags=re.DOTALL).strip()
