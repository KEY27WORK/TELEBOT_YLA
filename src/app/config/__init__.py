# app/config/__init__.py

"""
⚙️ Config Package — Централізована конфігурація застосунку.

Цей пакет відповідає за:
- Завантаження та управління всіма налаштуваннями (токени, API, JSON, YAML)
- Управління залежностями через DI-контейнер
- Автоматичну реєстрацію обробників та фіч

Основні компоненти:
- ConfigService — єдиний доступ до налаштувань і ключів
- container — DI-контейнер для створення всіх сервісів
- register_handlers — автоматична реєстрація всіх хендлерів
"""

from .config_service import ConfigService
from .setup.container import Container
from .setup.bot_registrar import BotRegistrar
from .setup.constants import generate_menu_pattern

__all__ = [
    "ConfigService",
    "Container",
    "register_handlers",
    "generate_menu_pattern",
]