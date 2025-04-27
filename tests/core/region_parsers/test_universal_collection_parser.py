"""
🧪 test_universal_collection_parser.py — unit-тести для UniversalCollectionParser

Перевіряє:
- Визначення валюти по URL
- Побудову повної URL-адреси
- Парсинг JSON-LD (з моком)
- Парсинг DOM (з моком)
"""

import pytest
from bs4 import BeautifulSoup
from core.parsing.collections.universal_collection_parser import UniversalCollectionParser


def test_detect_currency():
    assert UniversalCollectionParser("https://eu.youngla.com/collections/test").get_currency() == "EUR"
    assert UniversalCollectionParser("https://uk.youngla.com/collections/test").get_currency() == "GBP"
    assert UniversalCollectionParser("https://www.youngla.com/collections/test").get_currency() == "USD"
    assert UniversalCollectionParser("https://youngla.com/collections/test").get_currency() == "USD"


def test_build_full_url():
    parser = UniversalCollectionParser("https://eu.youngla.com/collections/test")
    assert parser._build_full_url("/products/test-item") == "https://eu.youngla.com/products/test-item"
    assert parser._build_full_url("https://eu.youngla.com/products/ready") == "https://eu.youngla.com/products/ready"

    parser_us = UniversalCollectionParser("https://youngla.com/collections/test")
    assert parser_us._build_full_url("/products/abc") == "https://www.youngla.com/products/abc"


@pytest.mark.asyncio
async def test_extract_product_links_jsonld(monkeypatch):
    parser = UniversalCollectionParser("https://eu.youngla.com/collections/test")

    async def fake_fetch_page():
        parser.page_source = '''
        <html>
        <script type="application/ld+json">
        {
          "@type": "CollectionPage",
          "mainEntity": {
            "itemListElement": [
              { "item": { "url": "https://example.com/products/1" } },
              { "item": { "url": "https://example.com/products/2" } }
            ]
          }
        }
        </script>
        </html>
        '''
        parser.soup = BeautifulSoup(parser.page_source, "html.parser")
        return True

    monkeypatch.setattr(parser, "fetch_page", fake_fetch_page)

    links = await parser.extract_product_links()
    assert links == [
        "https://example.com/products/1",
        "https://example.com/products/2"
    ]


@pytest.mark.asyncio
async def test_extract_product_links_dom(monkeypatch):
    parser = UniversalCollectionParser("https://www.youngla.com/collections/test")

    async def fake_fetch_page():
        parser.page_source = '''
        <html>
            <a href="/products/1">Link1</a>
            <a href="/products/2">Link2</a>
        </html>
        '''
        parser.soup = BeautifulSoup(parser.page_source, "html.parser")
        return True

    monkeypatch.setattr(parser, "fetch_page", fake_fetch_page)

    links = await parser.extract_product_links()
    assert links == [
        "https://www.youngla.com/products/1",
        "https://www.youngla.com/products/2"
    ]
