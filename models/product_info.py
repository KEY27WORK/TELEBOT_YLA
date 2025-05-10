"""
📦 ProductInfo — структура для збереження інформації про товар YoungLA.

Використовується для передачі даних між парсером і Telegram-обробником.
"""

from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ProductInfo:
    title: str
    price: float
    description: str
    image_url: str
    weight: float
    colors_text: str
    images: List[str]
    currency: str
    sections: dict  # ⬅️ добавь это