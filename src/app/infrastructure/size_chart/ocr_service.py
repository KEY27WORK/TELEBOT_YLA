# 🧠 app/infrastructure/size_chart/ocr_service.py
"""
🧠 ocr_service.py — модуль OCR-розпізнавання таблиць розмірів через OpenAI Vision.

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

# 🔠 Системні імпорти
import logging                                                    # 🧾 Логування
import base64                                                    # 🖼️ Кодування зображення у base64
import json                                                      # 📦 JSON-декодування
import re                                                        # 🔍 Регулярні вирази для очистки
from typing import Optional, Dict                                # 🧰 Типізація

# 🧩 Внутрішні модулі
from app.infrastructure.ai.open_ai_serv import OpenAIService     # 🤖 GPT-інтерфейс
from app.infrastructure.ai.prompt_service import PromptService   # 💬 Генерація промтів
from app.shared.utils.prompts import ChartType                   # 📊 Тип таблиці розмірів
from app.shared.utils.logger import LOG_NAME                     # 🧾 Імʼя логера для OCR

logger = logging.getLogger(f"{LOG_NAME}.ocr")                    # 🧾 Ініціалізація логера


# ================================
# 📷 КЛАС OCR-СЕРВІСУ
# ================================
class OCRService:
    """ 📷 Клас для OCR через OpenAI GPT-4 Vision API. """

    def __init__(self, openai_service: OpenAIService, prompt_service: PromptService):
        """
        🔌 Ініціалізація OCR-сервісу з впровадженими залежностями.

        Args:
            openai_service (OpenAIService): 🤖 Інтерфейс до GPT-4 Vision
            prompt_service (PromptService): 💬 Генератор промтів для OCR
        """
        self.openai_service = openai_service								# 🤖 GPT API
        self.prompt_service = prompt_service								# 💬 Отримання промтів

    async def recognize(self, image_path: str, size_chart_type: ChartType) -> Optional[Dict]:
        """
        📥 Основний метод OCR-розпізнавання таблиці розмірів.

        Args:
            image_path (str): 📸 Шлях до зображення з таблицею
            size_chart_type (ChartType): 📊 Тип таблиці (e.g., MenTop, WomenBottom...)

        Returns:
            Optional[Dict]: 📋 Словник з JSON-даними або None при помилці
        """
        logger.info(f"🔍 OCR запущено для: {image_path} | Тип: {size_chart_type.value}")

        try:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")					# 🖼️ Кодуємо зображення в base64

            prompt = self.prompt_service.get_size_chart_prompt(size_chart_type)						# 💬 Отримуємо промт під конкретний тип таблиці

            response_text = await self.openai_service.chat_completion_with_vision(
                prompt=prompt,
                image_base64=encoded_image
            )

            if not response_text:
                raise ValueError("Отримано порожню відповідь від OpenAI Vision.")					# ❗ OpenAI повернув пусту відповідь

            logger.info(f"✅ OCR-відповідь:\n{response_text}")
            clean_text = self._clean_json_text(response_text)										# 🧹 Витягуємо JSON з markdown
            return json.loads(clean_text)															# 📦 Перетворюємо в словник

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Помилка обробки відповіді OCR: {e}")
            return None

        except Exception as e:
            logger.error(f"❌ Критична помилка OCR: {e}")
            return None

    @staticmethod
    def _clean_json_text(json_text: str) -> str:
        """
        🧹 Очищує markdown-обгортку (```json ... ```) з відповіді GPT.

        Args:
            json_text (str): 📄 Відповідь GPT як рядок

        Returns:
            str: 🧼 Чистий JSON-текст без маркування
        """
        match = re.search(r"```json\n(.*?)\n```", json_text, re.DOTALL)
        return match.group(1).strip() if match else json_text.strip()
