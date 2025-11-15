# tests/url_strategy_youngla_test.py
import pytest

# Тестируем ровно стратегию YoungLA
from app.infrastructure.url.youngla_strategy import YoungLAUrlStrategy


# ─────────────────────────────────────────────────────────────────────
# 🔧 Тестовые заглушки и фикстуры
# ─────────────────────────────────────────────────────────────────────
class _CfgStub:
    """Минимальный конфиг-сервис с .get('regions') для стратегии."""
    def __init__(self, regions: dict):
        self._regions = regions

    def get(self, key: str, default=None):
        if key == "regions":
            return self._regions
        return default


@pytest.fixture()
def cfg_stub():
    # Соответствует твоему app/config/00_regions.yaml, но компактно
    return _CfgStub(
        regions={
            "us": {"base_url": "https://www.youngla.com", "currency": "USD"},
            "eu": {"base_url": "https://eu.youngla.com", "currency": "EUR"},
            "uk": {"base_url": "https://uk.youngla.com", "currency": "GBP"},
        }
    )


@pytest.fixture()
def strategy(cfg_stub) -> YoungLAUrlStrategy:
    return YoungLAUrlStrategy(config=cfg_stub)  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────
# supports(domain)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "domain,expected",
    [
        ("youngla.com", True),                 # root US
        ("www.youngla.com", True),             # www → нормализуется
        ("shop.youngla.com", True),            # сабдомен US
        ("eu.youngla.com", True),              # root EU
        ("blog.eu.youngla.com", True),         # сабдомен EU
        ("uk.youngla.com", True),              # root UK
        ("news.uk.youngla.com", True),         # сабдомен UK
        ("youngla.com:443", True),             # с портом → нормализация
        ("example.com", False),
        ("young-la.com", False),
        ("youngxla.com", False),
        ("eu.youngla.co", False),
    ],
)
def test_supports(strategy: YoungLAUrlStrategy, domain: str, expected: bool):
    assert strategy.supports(domain) is expected


# ─────────────────────────────────────────────────────────────────────
# is_product_url(url)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youngla.com/products/alpha-tee", True),
        ("https://eu.youngla.com/products/alpha-tee?ref=123", True),
        ("https://uk.youngla.com/products/alpha-tee#hash", True),
        ("https://shop.youngla.com/products/alpha-tee", True),  # сабдомен
        ("https://www.youngla.com/collections/tops", False),    # коллекция, не продукт
        ("https://www.youngla.com/product/alpha-tee", False),   # нет /products/
        ("https://example.com/products/alpha-tee", False),      # чужой домен
    ],
)
def test_is_product_url(strategy: YoungLAUrlStrategy, url: str, expected: bool):
    assert strategy.is_product_url(url) is expected


# ─────────────────────────────────────────────────────────────────────
# is_collection_url(url)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youngla.com/collections/tops", True),
        ("https://eu.youngla.com/collections/new", True),
        ("https://uk.youngla.com/collections/sale?sort=asc", True),
        ("https://blog.eu.youngla.com/collections/whatever", True),  # сабдомен
        ("https://www.youngla.com/products/alpha-tee", False),
        ("https://example.com/collections/tops", False),
        ("https://www.youngla.com/collection/tops", False),  # нет /collections/
    ],
)
def test_is_collection_url(strategy: YoungLAUrlStrategy, url: str, expected: bool):
    assert strategy.is_collection_url(url) is expected


# ─────────────────────────────────────────────────────────────────────
# extract_product_slug(url)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url,slug",
    [
        ("https://www.youngla.com/products/alpha-tee", "alpha-tee"),
        ("https://eu.youngla.com/products/ALPHA-TEE", "ALPHA-TEE"),  # регистр не трогаем
        ("https://uk.youngla.com/products/alpha-tee?ref=1", "alpha-tee"),
        ("https://shop.youngla.com/products/alpha-tee/", "alpha-tee"),
        ("https://www.youngla.com/products/", None),                 # пустой slug
        ("https://www.youngla.com/collections/tops", None),          # не продуктовый путь
        ("https://example.com/products/alpha-tee", "alpha-tee"),     # метод не валидирует домен
        ("not a url at all", None),
    ],
)
def test_extract_product_slug(strategy: YoungLAUrlStrategy, url: str, slug: str | None):
    assert strategy.extract_product_slug(url) == slug


# ─────────────────────────────────────────────────────────────────────
# get_currency(url) + get_region_label(url)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url,currency,label",
    [
        ("https://www.youngla.com/products/alpha-tee", "USD", "US 🇺🇸"),
        ("https://eu.youngla.com/collections/new", "EUR", "EU 🇪🇺"),
        ("https://uk.youngla.com/collections/sale", "GBP", "UK 🇬🇧"),
        ("https://blog.eu.youngla.com/products/x", "EUR", "EU 🇪🇺"),  # сабдомен
        ("https://example.com/products/x", None, "Unknown"),
    ],
)
def test_currency_and_region_label(strategy: YoungLAUrlStrategy, url: str, currency: str | None, label: str):
    assert strategy.get_currency(url) == currency
    assert strategy.get_region_label(url) == label


# ─────────────────────────────────────────────────────────────────────
# get_base_url(currency) + build_product_url(region_code, path)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "currency,expected",
    [
        ("USD", "https://www.youngla.com"),
        ("EUR", "https://eu.youngla.com"),
        ("GBP", "https://uk.youngla.com"),
        ("PLN", None),
        ("", None),
        (None, None),
    ],
)
def test_get_base_url(strategy: YoungLAUrlStrategy, currency, expected):
    assert strategy.get_base_url(currency) == expected


@pytest.mark.parametrize(
    "region_code,slug,expected",
    [
        ("us", "alpha-tee", "https://www.youngla.com/products/alpha-tee"),
        ("EU", "/alpha-tee", "https://eu.youngla.com/products/alpha-tee"),
        ("Uk", "folder/alpha", "https://uk.youngla.com/products/folder/alpha"),
        ("pl", "alpha", None),  # нет такого региона в конфиге
        ("", "alpha", None),
        ("us", "", None),
    ],
)
def test_build_product_url(strategy: YoungLAUrlStrategy, region_code: str, slug: str, expected: str | None):
    assert strategy.build_product_url(region_code, slug) == expected