import types

import pytest
from app.domain.products.entities import ProductInfo

# Здесь подразумевается, что есть helper для сборки парсера на статичном HTML.
# Если его нет, этот тест можно пропустить.
@pytest.mark.skip(reason="Provide parser fixture or static HTML if available")
async def test_base_parser_sections_and_stock_are_frozen(make_parser):
    parser = make_parser(html="""
        <html><head><title>Tee</title></head>
        <body>
          <h1>TEE</h1>
          <span class="price">$10.00</span>
        </body></html>
    """)
    info: ProductInfo = await parser.get_product_info()
    assert isinstance(info.sections, types.MappingProxyType)
    assert isinstance(info.stock_data, types.MappingProxyType)
    