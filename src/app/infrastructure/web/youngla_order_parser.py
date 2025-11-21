# 🧾 src/app/infrastructure/web/youngla_order_parser.py
"""
🧾 youngla_order_parser.py — розбір .txt-файлів із позиціями YoungLA.

🔹 Підтримує два формати: окремі рядки Color/Size та комбіновані Color+Size.
🔹 Повертає впорядкований список товарів, кожен з яких містить кольори й розміри.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import re
from dataclasses import dataclass, field
from typing import Dict, List


# ================================
# 🧱 ДАНІ ТОВАРУ
# ================================
@dataclass(slots=True)
class YoungLAOrderProduct:
    """
    📦 Представляє позицію з файлу замовлень YoungLA.

    Attributes:
        sku: Код товару (наприклад, "4007").
        name: Людське ім'я товару.
        variants: Словник {колір: {розмір: кількість}}.
    """

    sku: str
    name: str
    variants: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def ensure_color(self, color: str) -> Dict[str, int]:
        """
        Гарантує наявність кошика для конкретного кольору.
        """
        color_key = color.strip()
        if color_key not in self.variants:
            self.variants[color_key] = {}
        return self.variants[color_key]

    def add_item(self, color: str, size: str, quantity: int) -> None:
        """
        Додає (або збільшує) кількість для конкретного розміру.
        """
        bucket = self.ensure_color(color)
        size_key = size.strip()
        bucket[size_key] = bucket.get(size_key, 0) + quantity


# ================================
# 🔤 РЕГУЛЯРНІ ВИРАЗИ
# ================================
_SKU_LINE_RE = re.compile(r"^(?P<sku>\d+)\s*-\s*(?P<name>.+)$")
_COLOR_AND_SIZE_RE = re.compile(
    r"^Color:\s*(?P<color>[^;]+);?\s*Size:\s*(?P<size>[^;]+);?\s*-\s*(?P<qty>\d+)",
    flags=re.IGNORECASE,
)
_COLOR_ONLY_RE = re.compile(r"^Color:\s*(?P<color>.+)$", flags=re.IGNORECASE)
_SIZE_LINE_RE = re.compile(r"^Size:\s*(?P<size>[^;]+);?\s*-\s*(?P<qty>\d+)", flags=re.IGNORECASE)


# ================================
# 📥 ПАРСЕР
# ================================
def parse_youngla_order_file(file_text: str) -> List[YoungLAOrderProduct]:
    """
    🧵 Конвертує текст файлу в перелік товарів із кольорами/розмірами.

    Args:
        file_text: Вміст .txt-файлу.

    Returns:
        Впорядкований список товарів з вкладеними словниками.
    """

    normalized = file_text.replace("\ufeff", "")  # Прибираємо BOM, якщо є
    products: List[YoungLAOrderProduct] = []
    current_product: YoungLAOrderProduct | None = None
    current_color: str | None = None

    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            current_color = None
            continue

        sku_line = _SKU_LINE_RE.match(line.rstrip(":"))
        if sku_line:
            current_product = YoungLAOrderProduct(
                sku=sku_line.group("sku").strip(),
                name=sku_line.group("name").rstrip(":").strip(),
            )
            products.append(current_product)
            current_color = None
            continue

        if current_product is None:
            continue

        inline_match = _COLOR_AND_SIZE_RE.match(line)
        if inline_match:
            color = inline_match.group("color").strip()
            size = inline_match.group("size").strip()
            quantity = int(inline_match.group("qty"))
            current_product.add_item(color, size, quantity)
            current_color = color
            continue

        color_match = _COLOR_ONLY_RE.match(line)
        if color_match:
            current_color = color_match.group("color").rstrip(":").strip()
            current_product.ensure_color(current_color)
            continue

        size_match = _SIZE_LINE_RE.match(line)
        if size_match and current_color:
            size = size_match.group("size").strip()
            quantity = int(size_match.group("qty"))
            current_product.add_item(current_color, size, quantity)

    return products


__all__ = ["YoungLAOrderProduct", "parse_youngla_order_file"]
