# 🧠 app/domain/ai/interfaces/prompt_service_interface.py
"""
🧠 IPromptService — інтерфейс для генерації промтів OpenAI.
"""

from abc import ABC, abstractmethod


class IPromptService(ABC):
    """
    🔌 Інтерфейс сервісу генерації промтів.
    Дає змогу підключати різні LLM або реалізації без зміни домену.
    """

    @abstractmethod
    def get_weight_prompt(self, title: str, description: str, image_url: str) -> str:
        pass

    @abstractmethod
    def get_translation_prompt(self, text: str) -> str:
        pass

    @abstractmethod
    def get_slogan_prompt(self, title: str, description: str) -> str:
        pass

    @abstractmethod
    def get_music_prompt(self, description: str) -> str:
        pass

    @abstractmethod
    def get_hashtags_prompt(self, description: str) -> str:
        pass
