# 🧪 tests/infrastructure/web/test_youngla_order_parser.py
"""
🧪 Тести для `parse_youngla_order_file`.

Перевіряємо:
- підтримку міксу форматів (Color+Size в одному рядку та розділені);
- коректне згортання кількості в межах одного кольору/розміру;
- стабільну поведінку при відсутності вхідних даних.
"""

from __future__ import annotations

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.web.youngla_order_parser import (  # noqa: WPS221 (читабельний імпорт)
    YoungLAOrderProduct,
    parse_youngla_order_file,
)


def test_parse_youngla_order_file_mixed_formats() -> None:
    """Перевіряє змішаний формат Color/Size."""
    file_text = (
        "4007 - RAMBO CUT-OFFS:\n"
        "Color: Black/Dark Tree Camo\n"
        "Size: M; - 2\n"
        "Size: L; - 2\n"
        "Color: Heather Grey/Navy\n"
        "Size: L; - 4\n"
        "Size: M; - 3\n"
        "\n"
        "4117 - SUPERMAN COMPRESSION TEES:\n"
        "Color: Black; Size: L; - 2\n"
        "Color: Black; Size: M; - 2\n"
        "Color: Black/Red; Size: L; - 4\n"
        "Color: Charcoal; Size: S; - 2\n"
    )

    products = parse_youngla_order_file(file_text)

    assert len(products) == 2

    first = products[0]
    assert isinstance(first, YoungLAOrderProduct)
    assert first.sku == "4007"
    assert first.name == "RAMBO CUT-OFFS"
    assert first.variants["Black/Dark Tree Camo"]["M"] == 2
    assert first.variants["Black/Dark Tree Camo"]["L"] == 2
    assert first.variants["Heather Grey/Navy"]["L"] == 4
    assert first.variants["Heather Grey/Navy"]["M"] == 3

    second = products[1]
    assert second.sku == "4117"
    assert second.name == "SUPERMAN COMPRESSION TEES"
    assert second.variants["Black"]["L"] == 2
    assert second.variants["Black"]["M"] == 2
    assert second.variants["Black/Red"]["L"] == 4
    assert second.variants["Charcoal"]["S"] == 2


def test_parse_youngla_order_file_accumulates_quantity() -> None:
    """Перевіряє сумування кількості для ідентичних варіантів."""
    file_text = (
        "5000 - Test Tee:\n"
        "Color: Navy\n"
        "Size: L; - 1\n"
        "Size: L; - 2\n"
    )

    products = parse_youngla_order_file(file_text)

    assert len(products) == 1
    only_product = products[0]
    assert only_product.variants["Navy"]["L"] == 3


def test_parse_youngla_order_file_empty_input() -> None:
    """Повертає порожній список, якщо текст без даних."""
    assert parse_youngla_order_file("") == []
