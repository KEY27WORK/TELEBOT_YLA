# tests/content/conftest.py
import pytest
from dataclasses import dataclass
from app.infrastructure.content.product_content_service import ProductContentService
from app.domain.products.entities import ProductInfo
from decimal import Decimal

# --- Стабы зависимостей ---
class FakeTranslator:
    async def generate_slogan(self, *, title: str, description: str) -> str:
        # стаб: <=10 слов, без кавычек (как прод-валидация)
        return f"{title.split()[0]} vibe everyday drive"

    async def translate_sections(self, *, text: str) -> dict[str, str]:
        # стаб: сделаем 2-3 секции, в т.ч. зависимые от входа
        return {
            "МАТЕРІАЛ": "Бавовна 100%",
            "ОПИС": f"Опис: {text[:40]}",
        }

class FakeHashtags:
    async def generate(self, product: ProductInfo) -> set[str]:
        # стаб: детерминированный набор
        return {"#youngla", "#gym", "#athleisure"}

class FakePriceHandler:
    async def calculate_and_format(self, url: str):
        # контракт фасада: (obj, price_message, images)
        return object(), "💵 49.99 USD (final)", [
            "https://cdn.example/img1.jpg",
            "https://cdn.example/img2.jpg",
        ]

@pytest.fixture
def dto_product() -> ProductInfo:
    return ProductInfo(
        title="YLA123 Performance Tee",
        price=Decimal("49.99"),
        description="Ultra light tee for high-intensity workouts.",
        image_url="https://cdn.example/hero.jpg",
        images=("https://cdn.example/hero.jpg", "https://cdn.example/img2.jpg"),
        # остальные поля — по дефолту
    )

@pytest.fixture
def content_service():
    # Собираем сервис с фейковыми зависимостями
    return ProductContentService(
        translator=FakeTranslator(),
        hashtag_generator=FakeHashtags(),
        price_handler=FakePriceHandler(),
    )
