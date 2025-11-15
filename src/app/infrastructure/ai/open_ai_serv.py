# 📬 app/infrastructure/ai/open_ai_serv.py
"""
📬 Легковаговий клієнт OpenAI, який працює з нашим `ChatPrompt` DTO.

🔹 Конвертує повідомлення у формат OpenAI Chat і викликає chat/vision API.
🔹 Логує ключові параметри запиту (модель, temperature, наявність choices).
🔹 Масштабується на vision: додає base64-картинку у `content` для user-повідомлень.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import openai															# 🤖 Офіційний SDK OpenAI
from openai import RateLimitError										# 🚦 Обмеження запитів
from openai.types.chat import ChatCompletionMessageParam				# 📨 Типи API відповіді

# 🔠 Системні імпорти
import logging															# 🧾 Логи
from typing import Any, List, Optional, cast							# 📐 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService					# ⚙️ Конфіги з API-ключами
from app.shared.utils.logger import LOG_NAME							# 🏷️ Імʼя логера
from .dto import ChatMessage, ChatPrompt, Role							# 💬 Наші DTO


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai.openai")					# 🧾 Іменований логер


# ================================
# 🔄 КОНВЕРТЕР ПОВІДОМЛЕНЬ
# ================================
def _to_openai(messages: List[ChatMessage]) -> List[ChatCompletionMessageParam]:
    """🔄 Перетворює наші `ChatMessage` у формат OpenAI Chat API."""
    converted: List[ChatCompletionMessageParam] = []					# 📦 Результуючий список
    for message in messages:											# 🔁 Проходимо кожне повідомлення
        role_value = (
            message.role.value if isinstance(message.role, Role) else str(message.role)
        )																# 🎭 Витягуємо роль
        payload: Any = {"role": role_value, "content": message.content}	# 📝 Формуємо структуру
        converted.append(cast(ChatCompletionMessageParam, payload))	# 📥 Додаємо до списку
    logger.debug("🔄 to_openai converted=%d", len(converted))			# 🪵 Лог довжини
    return converted													# ↩️ Повертаємо результат


# ================================
# 🤖 OPENAI-СЕРВІС
# ================================
class OpenAIService:
    """🤖 Клієнт OpenAI для звичайних і vision-запитів."""

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(self, config_service: ConfigService) -> None:
        self._cfg = config_service										# ⚙️ Конфігураційний сервіс
        api_key = self._cfg.get("openai.api_key")						# 🔑 Ключ OpenAI
        if not api_key:													# 🚫 Переконуємось, що ключ присутній
            logger.critical("❌ OPENAI_API_KEY не знайдено")			# 🪵 Критичний лог
            raise ValueError("OPENAI_API_KEY is required")				# 🚨 Зупиняємо ініціалізацію
        self._client = openai.AsyncOpenAI(api_key=api_key)				# 🤖 Створюємо асинхронний клієнт
        logger.info("✅ OpenAIService ініціалізовано")					# 🪵 Фіксуємо успішний старт

    # ================================
    # 💬 CHAT-COMPLETION
    # ================================
    async def chat_completion(self, prompt: ChatPrompt) -> Optional[str]:
        """💬 Виконує класичний чат-запит та повертає текст відповіді."""
        try:
            model = cast(str, prompt.model or self._cfg.get("openai.model", "gpt-4o-mini"))  # 🤖 Обираємо модель
            temperature = float(getattr(prompt, "temperature", 0.3) or 0.3)					# 🌡️ Температура
            max_tokens = prompt.max_tokens													# 🔢 Обмеження токенів
            logger.debug(
                "📤 OpenAI chat request",
                extra={"model": model, "temperature": temperature, "max_tokens": max_tokens},
            )																				# 🪵 Лог запиту

            response = await self._client.chat.completions.create(							# 📡 Виклик API
                model=model,
                messages=_to_openai(prompt.messages),										# 📨 Конвертовані повідомлення
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if not response.choices:														# 🚫 Перевіряємо наявність відповіді
                logger.error("❌ Chat: відповідь OpenAI без choices")
                return None

            content = response.choices[0].message.content									# 📝 Перший варіант
            trimmed = content.strip() if content else None									# ✂️ Прибираємо зайві пробіли
            logger.debug(
                "📥 OpenAI chat response",
                extra={"has_content": bool(trimmed), "finish_reason": response.choices[0].finish_reason},
            )																				# 🪵 Лог результату
            return trimmed																	# ↩️ Текст відповіді

        except RateLimitError as exc:
            logger.error(
                "🚦 Chat: RateLimitError від OpenAI",
                extra={
                    "model": locals().get("model"),
                    "temperature": locals().get("temperature"),
                    "max_tokens": locals().get("max_tokens"),
                    "error": str(exc),
                },
            )																				# 🪵 Сигнал про ліміт
            return None
        except openai.APIError as exc:
            logger.error("❌ Chat: OpenAI APIError: %s", exc, exc_info=True)					# 🪵 Деталі помилки
            return None

    # ================================
    # 🖼️ CHAT-COMPLETION + VISION
    # ================================
    async def chat_completion_with_vision(self, *, prompt: ChatPrompt, image_base64: str) -> Optional[str]:
        """
        🖼️ Виконує мультимодальний запит: текст + base64-картинка.

        Args:
            prompt: Підготовлений `ChatPrompt`.
            image_base64: Зображення у base64 (PNG).
        """
        try:
            model = cast(str, prompt.model or self._cfg.get("openai.vision_model", "gpt-4o-mini"))  # 🤖 Vision-модель
            temperature = float(getattr(prompt, "temperature", 0.2) or 0.2)							# 🌡️ Температура
            max_tokens = prompt.max_tokens															# 🔢 Ліміт токенів
            logger.debug(
                "📤 OpenAI vision request",
                extra={"model": model, "temperature": temperature, "max_tokens": max_tokens},
            )																						# 🪵 Параметри запиту

            messages: List[ChatCompletionMessageParam] = []										# 📨 Фінальний список
            data_url = f"data:image/png;base64,{image_base64}"									# 🖼️ Data URL для OpenAI

            for message in prompt.messages:														# 🔁 Обробляємо кожне повідомлення
                role_value = (
                    message.role.value if isinstance(message.role, Role) else str(message.role)
                )																				# 🎭 Роль
                if role_value == "user":															# 👤 user → мультимодальний контент
                    content_blocks = [
                        {"type": "text", "text": str(message.content)},							# 📝 Текст
                        {"type": "image_url", "image_url": {"url": data_url}},					# 🖼️ Зображення
                    ]
                    payload = {"role": "user", "content": content_blocks}						# 📦 Payload
                else:
                    payload = {"role": role_value, "content": str(message.content)}				# 📄 Текст для system/assistant
                messages.append(cast(ChatCompletionMessageParam, payload))						# 📮 Додаємо у чергу

            response = await self._client.chat.completions.create(								# 📡 Виклик API
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if not response.choices:																# 🚫 Перевіряємо наявність результату
                logger.error("❌ Vision: порожній choices")
                return None

            content = response.choices[0].message.content										# 📝 Текст відповіді
            trimmed = content.strip() if content else None										# ✂️ Прибираємо пробіли
            logger.debug(
                "📥 OpenAI vision response",
                extra={"has_content": bool(trimmed), "finish_reason": response.choices[0].finish_reason},
            )																					# 🪵 Звіт
            return trimmed																		# ↩️ Повертаємо текст

        except RateLimitError as exc:
            logger.error(
                "🚦 Vision: RateLimitError від OpenAI",
                extra={
                    "model": locals().get("model"),
                    "temperature": locals().get("temperature"),
                    "max_tokens": locals().get("max_tokens"),
                    "error": str(exc),
                },
            )																				# 🪵 Сигнал про ліміт
            return None
        except openai.APIError as exc:
            logger.error("❌ Vision: OpenAI APIError: %s", exc, exc_info=True)					# 🪵 Деталі збою
            return None


__all__ = ["OpenAIService"]											# 📦 Експортований сервіс
