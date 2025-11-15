# ⚙️ app/config/__init__.py
"""
⚙️ Пакет Config — централізована конфігурація та ініціалізація застосунку.

Цей пакет відповідає за:
- Завантаження та управління всіма налаштуваннями (.env, *.yaml з підпапок config/yamls).
- Створення та зв'язування всіх сервісів через DI‑контейнер.
- Реєстрацію обробників Telegram.
"""

# ================================
# 🧩 ПУБЛІЧНИЙ API ПАКЕТУ
# ================================
from typing import TYPE_CHECKING

from .config_service import ConfigService
from .setup.constants import CONST, AppConstants, generate_menu_pattern

if TYPE_CHECKING:  # лише для підказок типів, без виконання імпорту під час рантайму
    from .setup.bot_registrar import BotRegistrar
    from .setup.container import Container

# ================================
# 📤 EXPORT
# ================================

__all__ = [
    "AppConstants",
    "BotRegistrar",
    "ConfigService",
    "CONST",
    "Container",
    "generate_menu_pattern",
]


def __getattr__(name: str):
    if name == "Container":
        from .setup.container import Container  # локальний імпорт → немає циклу

        return Container
    if name == "BotRegistrar":
        from .setup.bot_registrar import BotRegistrar  # локальний імпорт → немає циклу

        return BotRegistrar
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
