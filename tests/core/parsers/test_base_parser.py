"""
🧪 test_base_parser.py — unit-тести для асинхронного парсера BaseParser (YoungLA)

Перевіряє:
- Витяг title, description, price, image_url, sections з мок-HTML
- Формування об'єкта ProductInfo
- Парсинг JSON-LD для кольорів/розмірів
"""

import pytest  # 📦 Фреймворк для тестування
from bs4 import BeautifulSoup  # 🧰 Парсер HTML
from core.parsers.base_parser import BaseParser  # 🧱 Основний парсер сторінки товару
from unittest.mock import AsyncMock, patch  # 🔧 Моки для Playwright

# 👇 Мок-HTML, що емулює сторінку YoungLA
TEST_HTML = """
<html>
  <head>
    <meta property="product:price:amount" content="39.99">
    <meta name="twitter:description" content="A test product for unit testing.">
    <meta property="og:image" content="https://test.com/image.jpg">
  </head>
  <body>
    <h1>Test Product</h1>
    <div class="product-gallery__thumbnail-list">
      <button><img src="//cdn.test.com/img1.jpg"></button>
      <button><img src="//cdn.test.com/img2.jpg"></button>
    </div>
    <div id="ProductAccordion">
      <details>
        <summary>Fabric</summary>
        <div>80% Cotton / 20% Polyester</div>
      </details>
    </div>
    <script type="application/ld+json">
    {
      "@type": "Product",
      "offers": [
        {"name": "Black / Large", "availability": "http://schema.org/InStock"},
        {"name": "White / Medium", "availability": "http://schema.org/OutOfStock"}
      ]
    }
    </script>
  </body>
</html>
"""

@pytest.mark.asyncio
@patch("core.parsers.base_parser.WebDriverService.fetch_page_source", new_callable=AsyncMock)
async def test_base_parser_parses_minimal_product(mock_fetch):
    # 🧪 Підставляємо мокнутий HTML замість реального завантаження через браузер
    mock_fetch.return_value = TEST_HTML

    parser = BaseParser(url="https://www.youngla.com/products/mock-product", enable_progress=False)
    
    # 📥 Отримуємо info-об'єкт з усіма полями
    product_info = await parser.get_product_info()

    # ✅ Тестуємо, чи коректно витягнуті основні поля
    assert product_info.title == "Test Product"
    assert product_info.price == 39.99
    assert product_info.description == "A test product for unit testing."
    assert product_info.image_url == "https://test.com/image.jpg"
    assert product_info.currency == "USD"

    # 🎨 Перевірка наявності кольору/розміру з JSON-LD
    assert "Black" in product_info.colors_text

    # 🖼 Перевірка галереї
    assert "img1.jpg" in product_info.images[0]

    # 📑 Перевірка секцій accordion
    assert product_info.sections == {"FABRIC": "80% Cotton / 20% Polyester"}

    # ⚖️ Вага має бути > 0 (оцінюється GPT або дається дефолт)
    assert product_info.weight > 0.0

    print("✅ BaseParser parsed all expected fields successfully.")
