
# 🧪 test_product_info_parser.py — тести для парсингу товару і ProductInfo

import pytest
from models.product_info import ProductInfo
from app.infrastructure.parsers.base_parser import BaseParser

# 🔧 Фіктивний HTML (можна розширити або мокнути WebDriver)
FAKE_HTML = '''
<html>
  <head>
    <meta property="product:price:amount" content="48.00">
    <meta name="twitter:description" content="Test description">
    <meta property="og:image" content="https://example.com/image.jpg">
  </head>
  <body>
    <h1>Test Product</h1>
    <div class="product-gallery__thumbnail-list">
      <button><img src="//cdn.example.com/img1.jpg" /></button>
    </div>
  </body>
</html>
'''

@pytest.mark.asyncio
async def test_product_info_parsing(monkeypatch):
    # 🧪 Мокаємо WebDriverService
    async def fake_fetch_page_source(self, url):
        return FAKE_HTML

    monkeypatch.setattr("core.webdriver.webdriver_service.WebDriverService.fetch_page_source", fake_fetch_page_source)

    parser = BaseParser("https://www.youngla.com/products/test", enable_progress=False)
    info: ProductInfo = await parser.get_product_info()

    assert isinstance(info, ProductInfo)
    assert info.title == "Test Product"
    assert info.price == 48.0
    assert info.description == "Test description"
    assert info.image_url == "https://example.com/image.jpg"
    assert info.currency == "USD"
    assert info.images[0].startswith("https://")
    assert info.weight > 0.0  # Вага визначається навіть без GPT при моканому конфігу
