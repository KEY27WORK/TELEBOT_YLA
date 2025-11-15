# 🤖 app/infrastructure/ai/__init__.py
"""
🤖 Інфраструктурний шар для AI-сервісів.

🔹 DTO (`ChatPrompt`, `ChatMessage`, `Role`) — легкі структури без SDK-залежностей.
🔹 `OpenAIService` — тонкий клієнт OpenAI, що працює з `ChatPrompt`.
🔹 `PromptService` — будівник промтів на базі `shared`-сервісу.
🔹 `AITaskService` — високорівневі задачі (вага, переклад, слогани).
"""

from __future__ import annotations

# 🧱 DTO
from .dto import ChatMessage, ChatPrompt, Role

# ☁️ OpenAI клієнт
from .open_ai_serv import OpenAIService

# 🧾 Побудова промтів
from .prompt_service import PromptService

# 🧠 Високорівневі задачі
from .ai_task_service import AITaskService

__all__ = [
    "ChatMessage",
    "ChatPrompt",
    "Role",
    "OpenAIService",
    "PromptService",
    "AITaskService",
]
