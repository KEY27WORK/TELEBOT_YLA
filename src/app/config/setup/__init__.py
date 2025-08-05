# cores/config/setup/__init__.py
"""
⚙️ Пакет для налаштування та 'збірки' всіх компонентів бота перед запуском.

Надає доступ до контейнера залежностей та реєстратора обробників.
"""

# "Піднімаємо" ключові компоненти на рівень пакета `setup`
from .container import Container
from .bot_registrar import BotRegistrar
from .constants import generate_menu_pattern

# Вказуємо, що саме експортується при `from . import *`
__all__ = [
    "Container",
    "BotRegistrar",
    "generate_menu_pattern",
]
