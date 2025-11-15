# 🧠 app/domain/ai/interfaces/prompt_service_interface.py
"""
🧠 IPromptService — інтерфейс для генерації промтів для мовних моделей.

🔹 Чистий домен: лише контракти й DTO, без залежностей від OpenAI чи інфри.
🔹 Типобезпека: роль як Literal, контент як структуровані TextPart / ImagePart.
🔹 Готовність до мультимодальності та A/B тестів.
"""

from __future__ import annotations

# 🔠 Стандартні імпорти
import logging                                                        # 🧾 Логування побудови промтів
from dataclasses import dataclass, field                               # 🧱 DTO зі слотами
from enum import Enum                                                  # 🧮 Тональність/мова
from typing import ClassVar, Literal, Optional, Protocol, Sequence, Union, runtime_checkable  # 🧰 Типізація

# 🧩 Внутрішні модулі
from app.shared.utils.logger import LOG_NAME                           # 🏷️ Базовий префікс логера

# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
MODULE_LOGGER_NAME: str = f"{LOG_NAME}.domain.ai.prompt_service"      # 🏷️ Префікс для сервісу промтів
logger = logging.getLogger(MODULE_LOGGER_NAME)                         # 🧾 Модульний логер
logger.debug("🧠 prompt_service_interface імпортовано")                # 🚀 Фіксуємо ініціалізацію


# ================================
# 🏛️ ДОМЕННІ DTO ТА ENUMS
# ================================
@dataclass(frozen=True, slots=True)
class ProductPromptDTO:
    """📦 DTO з даними про товар для генерації промптів."""

    title: str                                                          # 🏷️ Назва товару
    description: str                                                    # 📝 Опис для контексту
    image_url: Optional[str] = None                                     # 🖼️ (опційно) зображення


# 🎭 Ролі повідомлень
Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class TextPart:
    """✏️ Текстова частина повідомлення."""
    type: Literal["text"] = field(default="text", init=False)        # 🔠 Фіксоване поле типу
    text: str = ""                                                     # 📝 Вміст тексту


@dataclass(frozen=True, slots=True)
class ImagePart:
    """🖼️ Частина повідомлення з зображенням (для мультимодальності)."""
    type: Literal["image_url"] = field(default="image_url", init=False)  # 🏷️ Тип частини = image_url
    url: str = ""                                                         # 🌐 Посилання на зображення


ContentPart = Union[TextPart, ImagePart]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """💬 Повідомлення з роллю та мультимодальним контентом."""
    role: Role                                                              # 🎭 Роль повідомлення
    content: Sequence[ContentPart]                                          # 🪄 Послідовність контенту (text/image)


@dataclass(frozen=True, slots=True)
class ChatPrompt:
    """
    📦 Структурований промпт для чат-моделей.

    Метадані:
      • prompt_id — ідентифікатор для A/B тестів.
      • version — номер версії (допомагає відслідковувати зміни).
      • max_tokens — верхня межа токенів у відповіді (опціонально).
    """
    messages: Sequence[ChatMessage]                                           # 💬 Обов'язковий список повідомлень
    prompt_id: Optional[str] = None                                           # 🆔 Ідентифікатор для A/B експериментів
    version: int = 1                                                          # 🔢 Версія шаблону промпта
    max_tokens: Optional[int] = None                                          # 🔒 Обмеження відповіді моделі

    # невеличкий guard: порожні промти та некоректні ліміти
    def __post_init__(self):
        if not self.messages:                                                 # 🚫 Немає жодного повідомлення
            logger.error("🚫 ChatPrompt без повідомлень")
            raise ValueError("ChatPrompt must contain at least one message.")
        if self.max_tokens is not None and self.max_tokens <= 0:              # 🚫 Невалідний ліміт токенів
            logger.error("🚫 max_tokens <= 0 | value=%s", self.max_tokens)
            raise ValueError("max_tokens must be a positive integer when provided.")

    # зручні фабрики (не ламають існуюче API, просто допоміжні)
    @classmethod
    def user_text(cls, text: str, *, max_tokens: Optional[int] = None) -> "ChatPrompt":
        logger.debug("🧱 ChatPrompt.user_text | text_len=%d", len(text))  # 🧾 Лог для відстеження довжини запиту
        return cls(
            messages=[ChatMessage(role="user", content=[TextPart(text=text)])],  # 🙋 Єдине повідомлення від user
            max_tokens=max_tokens,                                                # 🔒 Опціональний ліміт токенів
        )

    @classmethod
    def system_user_text(
        cls,
        system: str,
        user: str,
        *,
        max_tokens: Optional[int] = None,
    ) -> "ChatPrompt":
        """Фабрика промпта зі зв'язкою system+user для швидкого шаблону."""  # 📋 Допоміжний конструктор
        logger.debug(
            "🧱 ChatPrompt.system_user_text | system_len=%d user_len=%d",
            len(system),
            len(user),
        )  # 🧾 Діагностика довжин system/user повідомлень
        return cls(
            messages=[
                ChatMessage(role="system", content=[TextPart(text=system)]),     # 🧠 Інструкції системи
                ChatMessage(role="user", content=[TextPart(text=user)]),         # 🙋 Вхід користувача
            ],
            max_tokens=max_tokens,                                                # 🔒 Обмеження відповіді
        )


class Tone(str, Enum):
    """🎨 Тональність для текстів."""
    NEUTRAL = "neutral"                                                 # 🟦 Збалансований стиль
    FRIENDLY = "friendly"                                               # 🟩 Дружній тон
    SALES = "sales"                                                     # 🟥 Акцент на продажі


class Lang(str, Enum):
    """🌍 Цільова мова для генерації/перекладу."""
    UK = "uk"                                                           # 🇺🇦 Українська
    EN = "en"                                                           # 🇬🇧 Англійська


# ================================
# 🏛️ ІНТЕРФЕЙС СЕРВІСУ ПРОМТІВ
# ================================
@runtime_checkable
class IPromptService(Protocol):
    """🔌 Контракт для сервісів генерації промтів."""

    def get_weight_prompt(self, product: ProductPromptDTO) -> ChatPrompt:
        """Підготувати промпт для задачі оцінки ваги товару."""  # ⚖️ Викликається перед IWeightEstimator
        ...

    def get_translation_prompt(self, text: str, target_lang: Lang = Lang.UK) -> ChatPrompt:
        """Побудувати промпт на переклад опису `text` до мови `target_lang`."""  # 🌐 Використовується Translator
        ...

    def get_slogan_prompt(self, product: ProductPromptDTO, tone: Tone = Tone.SALES) -> ChatPrompt:
        """Створити промпт для генерації слогану з певною тональністю."""  # ✨ Для ISloganGenerator
        ...

    def get_music_prompt(self, product: ProductPromptDTO) -> ChatPrompt:
        """Підготувати промпт, який підбирає музику під продукт."""  # 🎵 Для музичних рекомендацій
        ...

    def get_hashtags_prompt(self, product: ProductPromptDTO, lang: Lang = Lang.UK) -> ChatPrompt:
        """Побудувати промпт для генерації набору хештегів заданою мовою."""  # #️⃣ Для генератора хештегів
        ...


__all__ = [
    # Контракт
    "IPromptService",                                                         # 🔌 Публічний інтерфейс
    # DTO
    "ProductPromptDTO",                                                       # 📦 Дані про продукт
    "ChatPrompt",                                                             # 💬 Структура промпта
    "ChatMessage",                                                            # 💭 Повідомлення з роллю
    "TextPart",                                                               # ✏️ Текстовий елемент
    "ImagePart",                                                              # 🖼️ Зображення в промпті
    "ContentPart",                                                            # 🔀 Юніон типів контенту
    # Enums/Literals
    "Tone",                                                                   # 🎨 Тональність текстів
    "Lang",                                                                   # 🌍 Мова генерації
    "Role",                                                                   # 🎭 Ролі повідомлень
]
logger.debug("🔓 __all__ оголошено: %s", __all__)
