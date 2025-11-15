# tests/parsers/test_base_parser_contract.py
from typing import cast
from app.infrastructure.web.webdriver_service import WebDriverService
from app.infrastructure.ai.ai_task_service import AITaskService
from app.config.config_service import ConfigService
from app.domain.products.services.weight_resolver import WeightResolver
from app.shared.utils.url_parser_service import UrlParserService
import asyncio
from decimal import Decimal
from types import MappingProxyType

import pytest

from app.infrastructure.parsers.base_parser import BaseParser
from app.domain.products.entities import ProductInfo


# ──────────────────────────────────────────────────────────────────────────────
#                          🔧 Тестовые заглушки/фейки
# ──────────────────────────────────────────────────────────────────────────────

class _FakeWebDriver:
    """Возвращает заранее заданный HTML как есть."""
    def __init__(self, html: str):
        self._html = html

    async def get_page_content(self, url: str, **kwargs) -> str:
        # имитируем поведение async браузера
        await asyncio.sleep(0)
        return self._html


class _FakeTranslatorService:
    """Не используется в базовом парсинге — простая заглушка."""
    pass


class _FakeConfigService:
    """Возвращает значения только для ключей, требуемых BaseParser."""
    def get(self, key: str, default=None, cast=None):
        # описание: включён fallback и разумный порог
        if key == "parser.description_fallback.enabled":
            return True
        if key == "parser.description_fallback.min_len":
            return 20
        if key == "parser.bot_markers_extra":
            return None
        return default


class _FakeWeightResolver:
    async def resolve_g(self, title: str, description: str, image_url: str) -> int:
        await asyncio.sleep(0)
        return 800  # фиксированная "оценка" для предсказуемости тестов


class _FakeUrlParserService:
    def get_currency(self, url: str, default=None):
        return "USD"  # фиксированная валюта, чтобы не зависеть от реализаций


# ──────────────────────────────────────────────────────────────────────────────
#                               🧪 Вспомогалки
# ──────────────────────────────────────────────────────────────────────────────


def _make_parser(monkeypatch, html: str, *, extractor_cls=None) -> BaseParser:
    """
    Собирает BaseParser с фейковыми зависимостями.
    При необходимости подменяет HtmlDataExtractor на тестовый класс.
    """
    if extractor_cls is not None:
        # В base_parser импорт вот так: from .html_data_extractor import HtmlDataExtractor
        # поэтому патчим именно атрибут модуля base_parser.
        import app.infrastructure.parsers.base_parser as base_parser_mod
        monkeypatch.setattr(base_parser_mod, "HtmlDataExtractor", extractor_cls)

    return BaseParser(
        url="https://example.com/product/alpha-123",
        webdriver_service=cast(WebDriverService, _FakeWebDriver(html)),
        translator_service=cast(AITaskService, _FakeTranslatorService()),
        config_service=cast(ConfigService, _FakeConfigService()),
        weight_resolver=cast(WeightResolver, _FakeWeightResolver()),
        url_parser_service=cast(UrlParserService, _FakeUrlParserService()),
        enable_progress=False,
        html_parser="lxml",
        request_timeout_sec=1,
        images_limit=30,
    )


# ──────────────────────────────────────────────────────────────────────────────
#                            🧪 Тестовые Extractor'ы
# ──────────────────────────────────────────────────────────────────────────────

class _ExtractorEmpty:
    """Имитация страницы, где ничего не распарсилось (пустые значения)."""
    def __init__(self, soup): pass
    def extract_title(self): return None
    def extract_price(self): return None
    def extract_description(self): return None
    def extract_main_image(self): return None
    def extract_all_images(self): return []
    def extract_detailed_sections(self): return {}
    def extract_stock_from_json_ld(self): return {}
    def extract_stock_from_legacy(self): return {}


class _ExtractorNormal:
    """Имитация валидной карточки товара с данными."""
    def __init__(self, soup): pass
    def extract_title(self): return "Ultra Hoodie"
    def extract_price(self): return "19.99"
    def extract_description(self): return "Best hoodie. 100% cotton."
    def extract_main_image(self): return "https://cdn.example.com/img/main.jpg"
    def extract_all_images(self):
        # проверим кортеж + дедуп
        return [
            "https://cdn.example.com/img/main.jpg",
            "https://cdn.example.com/img/1.jpg",
            "https://cdn.example.com/img/1.jpg",  # дубликат
            "https://cdn.example.com/img/2.jpg",
        ]
    def extract_detailed_sections(self):
        return {"МАТЕРІАЛ": "100% cotton", "ПОСАДКА": "regular"}
    def extract_stock_from_json_ld(self):
        return {"Black": {"M": True, "L": False}}
    def extract_stock_from_legacy(self):
        return {}


# ──────────────────────────────────────────────────────────────────────────────
#                                    ТЕСТЫ
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_base_parser_contract_empty_html(monkeypatch):
    """
    Смок-тест: пустой HTML → BaseParser должен вернуть валидный ProductInfo,
    не падая исключениями.
    """
    parser = _make_parser(monkeypatch, html="", extractor_cls=_ExtractorEmpty)

    info = await parser.get_product_info()
    assert isinstance(info, ProductInfo)

    # Контрактные инварианты (acceptance):
    assert info.title.strip() != ""                      # title непустой (fallback из URL)
    assert isinstance(info.price, Decimal)               # Decimal — по контракту денег
    assert info.price == Decimal("0.0")                  # дефолт при ошибке парсинга
    assert isinstance(info.images, tuple)                # images — tuple
    assert isinstance(info.sections, MappingProxyType)   # sections — MappingProxyType
    assert isinstance(info.stock_data, MappingProxyType) # stock_data — MappingProxyType
    assert isinstance(info.weight_g, int) and info.weight_g >= 0


@pytest.mark.asyncio
async def test_base_parser_contract_cloudflare_like_html(monkeypatch):
    """
    Смок-тест: "Cloudflare/челлендж"-подобная страница (данные не извлекаются).
    Важно: парсер всё равно возвращает валидный ProductInfo.
    """
    cloudflare_html = "<html><head><title>Just a moment...</title></head><body>cf-challenge</body></html>"
    parser = _make_parser(monkeypatch, html=cloudflare_html, extractor_cls=_ExtractorEmpty)

    info = await parser.get_product_info()
    assert isinstance(info, ProductInfo)

    # Инварианты
    assert info.title.strip() != ""
    assert isinstance(info.price, Decimal)
    assert isinstance(info.images, tuple)
    assert isinstance(info.sections, MappingProxyType)
    assert isinstance(info.stock_data, MappingProxyType)


@pytest.mark.asyncio
async def test_base_parser_contract_normal_card(monkeypatch):
    """
    Нормальная карточка: заполняются поля, соблюдается типобезопасность.
    """
    html = "<html><head><title>Ultra Hoodie</title></head><body>ok</body></html>"
    parser = _make_parser(monkeypatch, html=html, extractor_cls=_ExtractorNormal)

    info = await parser.get_product_info()
    assert isinstance(info, ProductInfo)

    # Значения
    assert info.title == "Ultra Hoodie"
    assert info.price == Decimal("19.99")
    assert info.image_url == "https://cdn.example.com/img/main.jpg"

    # Типы/инварианты
    assert isinstance(info.images, tuple)
    assert info.images == (
        "https://cdn.example.com/img/main.jpg",
        "https://cdn.example.com/img/1.jpg",
        "https://cdn.example.com/img/2.jpg",
    )  # дедуп + порядок

    assert isinstance(info.sections, MappingProxyType)
    assert dict(info.sections) == {"МАТЕРІАЛ": "100% cotton", "ПОСАДКА": "regular"}

    assert isinstance(info.stock_data, MappingProxyType)
    # значения мапы доступны для чтения как dict()
    sd = {k: dict(v) for k, v in info.stock_data.items()}
    assert "Black" in sd
    assert set(sd["Black"].keys()) >= {"M", "L"}

    assert isinstance(info.weight_g, int) and info.weight_g >= 0