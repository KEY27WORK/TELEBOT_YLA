# 🤖 app/infrastructure/ai/open_ai_serv.py
"""
🤖 open_ai_serv.py — базовий сервіс для взаємодії з OpenAI API.
"""

# 🌐 Зовнішні бібліотеки
import openai                                                   # 🤖 Бібліотека OpenAI
from openai import RateLimitError                              # 🚫 Обробка ліміту запитів
from openai.types.chat import ChatCompletionMessageParam       # 📩 Типізація повідомлень

# 🔠 Системні імпорти
import logging                                                  # 🧾 Логування
from typing import Optional, List                               # 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService             # ⚙️ Сервіс конфігурації
from app.shared.utils.logger import LOG_NAME                    # 🏷️ Глобальна назва логів

# 🔊 Іменований логер для OpenAI
logger = logging.getLogger(f"{LOG_NAME}.openai")


# ================================
# 🏛️ КЛАС СЕРВІСУ OPENAI
# ================================
class OpenAIService:
    """
    🧠 Асинхронний сервіс для інкапсуляції всієї логіки роботи з OpenAI API.
    """

    def __init__(self, config_service: ConfigService):
        """
        ⚙️ Ініціалізація сервісу з впровадженням залежності ConfigService.
        """
        self.config = config_service                                                 # ⚙️ Отримуємо доступ до API ключа
        api_key = self.config.get("openai.api_key")                                 # 🔑 API-ключ із конфігу

        if not api_key:
            logger.critical("❌ OPENAI_API_KEY не знайдено!")                        # ❗ Якщо ключ відсутній — фатальна помилка
            raise ValueError("OPENAI_API_KEY is required for OpenAIService.")

        self.client = openai.AsyncOpenAI(api_key=api_key)                            # 🤖 Ініціалізуємо клієнта
        logger.info("✅ OpenAIService успішно ініціалізовано.")                      # 🟢 Успішна ініціалізація

    async def chat_completion(
        self,
        prompt: str,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        📩 Надсилає промт до моделі GPT і повертає текстову відповідь.
        """
        try:
            model = self.config.get("openai.model", "gpt-4-turbo")                 # 🧠 Модель GPT
            max_tokens = self.config.get("openai.max_tokens", 1024)                # 🔢 Ліміт токенів

            messages: List[ChatCompletionMessageParam] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})    # 📥 Системне повідомлення
            messages.append({"role": "user", "content": prompt})                # 👤 Користувацький промт

            logger.info(f"📤 Надсилання запиту до GPT (модель: {model})...")
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            if not response.choices:
                logger.error("❌ OpenAI повернув порожній список 'choices'.")        # ❗ Порожня відповідь
                return None

            content = response.choices[0].message.content
            if not content:
                logger.warning("⚠️ Модель не повернула текст у відповіді.")         # ⚠️ Порожній текст
                return None

            return content.strip()                                                  # 🧼 Обрізаємо пробіли і повертаємо

        except RateLimitError:
            logger.error("❌ Перевищено ліміт запитів до OpenAI (RateLimitError).")  # 🚫 Ліміт
            return None
        except openai.APIError as e:
            logger.error(f"❌ Невідома помилка API при зверненні до OpenAI: {e}", exc_info=True)  # ❌ Інша помилка
            return None

    async def chat_completion_with_vision(
        self,
        prompt: str,
        image_base64: str,
        temperature: float = 0.7,
        model: str = "gpt-4-turbo"
    ) -> Optional[str]:
        """
        🖼️ Надсилає запит до Vision-моделі, що включає текст та зображення.
        """
        logger.debug(f"📸 Відправка Vision-запиту до моделі {model}...")
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},                       # 📝 Текстовий промт
                            {
                                "type": "image_url",                                  # 🖼️ Зображення
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                temperature=temperature,
                max_tokens=1024,
            )

            if not response.choices or not response.choices[0].message.content:
                logger.warning("⚠️ Vision-модель не повернула текст у відповіді.")    # ⚠️ Порожня відповідь
                return None

            return response.choices[0].message.content.strip()                        # 🧼 Очищаємо і повертаємо

        except openai.APIError as e:
            logger.error(f"❌ Помилка API OpenAI Vision: {e}")                        # ❌ Vision API помилка
            return None
