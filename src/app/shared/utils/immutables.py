# 🧊 app/shared/utils/immutables.py
"""
🧊 Утиліти для імітації «заморожених» структур даних.

🔹 Конвертує словники, списки та набори у їхні незмінні аналоги.
🔹 Гарантує відсутність мутацій у глибині складних структур.
🔹 Дозволяє виявити фризнуті мапи через `is_frozen_mapping`.
"""

from __future__ import annotations

# 🔠 Системні імпорти
from collections.abc import Iterable, Mapping            # 🧰 Перевірки типів колекцій
from decimal import Decimal                              # 💵 Підтримка грошових значень
from enum import Enum                                    # 🏷️ Перерахування
from types import MappingProxyType                       # 🔒 Незмінна обгортка над dict
from typing import Any                                   # 🧰 Загальний тип для даних

# ================================
# 🧾 АЛІАСИ
# ================================
FrozenMapping = MappingProxyType                         # 🔄 Псевдонім для читаємості


# ================================
# ❄️ ЗАМОРОЖУВАЧ СТРУКТУР
# ================================
def freeze(obj: Any) -> Any:
    """Рекурсивно перетворює колекції на незмінні аналоги."""
    if obj is None or isinstance(  # 🧱 Швидкий шлях для скалярів
        obj,
        (str, bytes, int, float, bool, Decimal, Enum),
    ):
        return obj
    if isinstance(obj, Mapping):   # 🧭 Словники → MappingProxyType
        return MappingProxyType({key: freeze(value) for key, value in obj.items()})
    if isinstance(obj, set):       # 🧮 Множини → frozenset
        return frozenset(freeze(value) for value in obj)
    if isinstance(obj, (list, tuple)) or _is_iterable_but_not_str(obj):  # 🔁 Послідовності
        try:
            return tuple(freeze(value) for value in obj)  # 🎯 Універсальна незмінна форма
        except TypeError:                                  # ⚠️ Одноразово-ітеровані обʼєкти
            return obj                                    # ↩️ Повертаємо як є
    return obj                                            # ⚖️ Для решти типів залишаємо без змін


# ================================
# 🔍 ПЕРЕВІРКИ
# ================================
def is_frozen_mapping(obj: Any) -> bool:
    """Перевіряє, чи є обʼєкт замороженою мапою (`freeze(dict)`)."""
    return isinstance(obj, MappingProxyType)


def _is_iterable_but_not_str(obj: Any) -> bool:
    """Визначає, чи є обʼєкт ітерованим, але не рядком або байтовою послідовністю."""
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))
