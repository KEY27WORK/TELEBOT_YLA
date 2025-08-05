# 🤖 app/infrastructure/ai/__init__.py
"""
🤖 Пакет `ai`

Містить сервіси для взаємодії зі штучним інтелектом (OpenAI).

- `OpenAIService` — базовий клієнт для роботи з API OpenAI.
- `TranslatorService` — сервіс для перекладу тексту через AI.
- `PromptService` — сервіс для генерації промтів для AI.
"""

from .open_ai_serv import OpenAIService
from .translator import TranslatorService
from .prompt_service import PromptService

__all__ = [
    "OpenAIService",
    "TranslatorService",
    "PromptService",
]
