# 📏 src/app/shared/utils/size_norm.py
"""
📏 size_norm.py — забезпечує уніфіковану нормалізацію токенів розмірів.

🔹 Приводить числові та літеральні розміри до стандартного вигляду.
🔹 Підтримує кириличні помилки (наприклад, «хl» → «XL»).
🔹 Інтегрує aliases з конфігурації для додаткових синонімів.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import re                                                   # 🧪 Регулярні вирази для очищення

# 🔠 Системні імпорти
from typing import Dict, Mapping, Optional                  # 🧰 Типізація структур даних

# 🧩 Внутрішні модулі проєкту

__all__ = ["normalize_size_token", "normalize_stock_map"]

# ================================
# ⚙️ КОНСТАНТИ МОДУЛЯ
# ================================
_MAX_X_REPEATS = 4                                          # 🧮 Максимальна кількість X у літеральних розмірах
_CYRILLIC_TO_LATIN = {"х": "x"}                             # 🔤 Перетворення кириличних літер у латиницю


# ================================
# 🧹 ПРИВАТНІ ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _basic_clean(token: str) -> str:
    """
    🧹 Очищує сирий токен: трім, нижній регістр, заміна кирилиці та фільтр символів.

    Args:
        token (str): Вхідний рядок з розміром.

    Returns:
        str: Нормалізований рядок, що містить лише [0-9a-z].
    """
    cleaned = (token or "").strip().lower()                 # ✂️ Обрізаємо пробіли та готуємо регістр
    if not cleaned:
        return ""

    for cyrillic, latin in _CYRILLIC_TO_LATIN.items():
        cleaned = cleaned.replace(cyrillic, latin)          # 🔄 Замінюємо кириличні символи на латинські

    return re.sub(r"[^0-9a-z]", "", cleaned)                # 🧼 Відкидаємо все, що не цифри та латинські літери


def _x_block_to_size(x_block: str) -> Optional[str]:
    """
    ❌ Перетворює послідовність 'x...' у відповідну частину позначення розміру.

    Args:
        x_block (str): Фрагмент, що складається лише з символів 'x'.

    Returns:
        Optional[str]: Рядок з великою літерою `X` або None, якщо шаблон недійсний.
    """
    if not x_block:
        return None
    if len(x_block) > _MAX_X_REPEATS:
        return None
    return "X" * len(x_block)                               # ❎ Формуємо частину типу 'XX' тощо


def _canonical_from_core_rules(cleaned: str) -> Optional[str]:
    """
    📐 Застосовує базові правила нормалізації без aliases.

    Args:
        cleaned (str): Вже очищений токен.

    Returns:
        Optional[str]: Канонічний розмір (наприклад, 'XS', '28') або None, якщо не співпало.
    """
    if not cleaned:
        return None

    if cleaned.isdigit():
        return cleaned

    match_multi = re.fullmatch(r"([234])xl", cleaned)       # 🔁 Підтримка записів на кшталт 2XL/3XL/4XL
    if match_multi:
        multiplier = int(match_multi.group(1))              # 🧮 Отримуємо множник для 'X'
        return "X" * multiplier + "L"                       # 📏 Перетворюємо на канонічний запис

    match_tail = re.fullmatch(r"(x{1,4})(s|l)", cleaned)    # 🧵 Патерн для XS/XL/XXL…
    if match_tail:
        x_part = _x_block_to_size(match_tail.group(1))      # 🧮 Формуємо кількість X
        tail = match_tail.group(2).upper()                  # 🔠 Приводимо суфікс до верхнього регістру
        if x_part:
            return f"{x_part}{tail}"                        # 🧷 Склеюємо канонічний розмір

    # Shopify інколи повертає суфіксами Small/Large (наприклад, "XXSmall" або "XXLarge")
    match_word_tail = re.fullmatch(r"(x{1,4})(small|large)", cleaned)
    if match_word_tail:
        x_part = _x_block_to_size(match_word_tail.group(1))
        if x_part:
            suffix = match_word_tail.group(2)
            tail = "S" if suffix.startswith("s") else "L"
            return f"{x_part}{tail}"

    if cleaned in {"s", "m", "l"}:
        return cleaned.upper()

    return None


def _prepare_alias_map(raw_aliases: Optional[Mapping[str, str]]) -> Dict[str, str]:
    """
    🗃️ Підготовлює мапу aliases для швидкого пошуку.

    Args:
        raw_aliases (Mapping[str, str] | None): Сирі дані з конфігурації.

    Returns:
        Dict[str, str]: Мапа очищених ключів до канонічних значень.
    """
    if not raw_aliases:
        return {}

    prepared: Dict[str, str] = {}
    for raw_key, raw_value in raw_aliases.items():
        cleaned_key = _basic_clean(str(raw_key))            # 🪟 Уніфікуємо ключ alias
        if not cleaned_key:
            continue

        value = (raw_value or "").strip()                   # 🧵 Працюємо з оригінальним значенням
        if not value:
            continue

        canonical = _canonical_from_core_rules(_basic_clean(value)) or value.upper()  # 🧭 Визначаємо кінцевий розмір
        prepared[cleaned_key] = canonical                    # 📌 Запам'ятовуємо у мапі

    return prepared


# ================================
# 🎯 ПУБЛІЧНІ ФУНКЦІЇ
# ================================
def normalize_size_token(raw: str, *, aliases: Optional[Mapping[str, str]] = None) -> str:
    """
    🎯 Нормалізує окремий токен розміру з урахуванням aliases.

    Args:
        raw (str): Вхідний розмір у довільному форматі.
        aliases (Mapping[str, str] | None): Мапа синонімів з конфігурації.

    Returns:
        str: Канонічний розмір або порожній рядок, якщо розпізнати не вдалося.
    """
    if not raw:
        return ""

    cleaned = _basic_clean(raw)                             # 🧹 Проводимо базове очищення токена
    if not cleaned:
        return ""

    core = _canonical_from_core_rules(cleaned)              # 🧭 Пробуємо побудувати канонічний розмір з правил ядра
    if core:
        return core

    alias_map = _prepare_alias_map(aliases)                 # 🗃️ Підготовлене відображення aliases
    if cleaned in alias_map:
        return alias_map[cleaned]                           # 🪄 Повертаємо розмір з конфігурації

    return ""


def normalize_stock_map(
    stock: Mapping[str, Mapping[str, bool]] | Dict[str, Dict[str, bool]] | None,
    *,
    locale: Optional[str] = None,
    aliases: Optional[Mapping[str, str]] = None,
) -> Dict[str, Dict[str, bool]]:
    """
    🗄️ Нормалізує карту наявності товарів за розмірами.

    Args:
        stock (Mapping[str, Mapping[str, bool]] | Dict[str, Dict[str, bool]] | None):
            Початкова структура зі stock-data.
        locale (str | None): Зарезервований аргумент (для сумісності, зараз не використовується).
        aliases (Mapping[str, str] | None): Мапа синонімів розмірів.

    Returns:
        Dict[str, Dict[str, bool]]: Скопійована структура з канонічними розмірами.
    """
    if not stock:
        return {}

    normalized: Dict[str, Dict[str, bool]] = {}             # 📦 Фінальний словник з нормалізованими даними

    for color, sizes in stock.items():
        if not color or not sizes:
            continue

        normalized_sizes: Dict[str, bool] = {}              # 🎯 Мапа нормалізованих розмірів для кольору

        for size_token, available in sizes.items():
            normalized_token = normalize_size_token(size_token, aliases=aliases)  # 📏 Уніфікуємо токен
            if not normalized_token:
                continue
            normalized_sizes[normalized_token] = bool(available)  # ✅ Фіксуємо наявність

        if normalized_sizes:
            normalized[str(color)] = normalized_sizes       # 📦 Додаємо тільки ненульові результати

    return normalized
