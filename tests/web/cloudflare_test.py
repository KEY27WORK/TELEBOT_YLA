# -*- coding: utf-8 -*-
import asyncio
import types
import pytest

# Тестируем целевой сервис
from app.infrastructure.web.webdriver_service import WebDriverService


# ───────────────────────────────────────────────────────────────────────────
# ФЕЙКИ ДЛЯ КОНТЕКСТА/СТРАНИЦЫ/РЕСПОНСА (без реального Playwright)
# ───────────────────────────────────────────────────────────────────────────

class FakeResponse:
    def __init__(self, status: int | None):
        self._status = status

    @property
    def status(self):
        return self._status


class FakePage:
    def __init__(self, statuses_seq: list[int | None], html_seq: list[str]):
        self._statuses = list(statuses_seq)
        self._htmls = list(html_seq)
        self._goto_calls = 0
        self._closed = False

    async def goto(self, url: str, wait_until: str, timeout: int):
        self._goto_calls += 1
        status = self._statuses.pop(0) if self._statuses else None
        return FakeResponse(status)

    async def content(self) -> str:
        # возвращаем текущий HTML на этой попытке (или последний)
        idx = min(self._goto_calls - 1, len(self._htmls) - 1)
        return self._htmls[idx] if self._htmls else ""

    async def close(self):
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed


class FakeContext:
    def __init__(self, page: FakePage):
        self._page = page
        # для совместимости, у реального есть ctx.tracing.start/stop
        self.tracing = types.SimpleNamespace(
            start=lambda **kwargs: asyncio.sleep(0),
            stop=lambda **kwargs: asyncio.sleep(0),
        )

    async def new_page(self) -> FakePage:
        return self._page

    async def close(self):
        pass


# ───────────────────────────────────────────────────────────────────────────
# ХЕЛПЕР: подготавливаем сервис к «сухому» режиму без реального браузера
# ───────────────────────────────────────────────────────────────────────────

def make_service_with_fakes(cfg=None) -> WebDriverService:
    cfg = cfg or types.SimpleNamespace(
        get=lambda *args, **kwargs: None  # минимальный заглушечный ConfigService.get
    )
    svc = WebDriverService(config_service=cfg)  # type: ignore[arg-type]

    # Выключаем всё лишнее
    svc._enable_stealth = False
    svc._trace_enabled = False
    svc._network_idle_wait_ms = 0
    svc._retry_delay_sec = 0

    # Мокаем startup/shutdown, чтобы не поднимать реальный браузер
    async def no_startup(): ...
    async def no_shutdown(): ...
    svc.startup = no_startup  # type: ignore[assignment]
    svc.shutdown = no_shutdown  # type: ignore[assignment]

    return svc


# ───────────────────────────────────────────────────────────────────────────
# ТЕСТЫ
# ───────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cloudflare_html_triggers_retries_and_fails(monkeypatch):
    """
    Мокаем «Just a moment…» в HTML, убеждаемся, что сервис ретраит N раз и возвращает None.
    """
    svc = make_service_with_fakes()

    # HTML Cloudflare splash на всех попытках
    html = "<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>"
    page = FakePage(statuses_seq=[200, 200, 200], html_seq=[html, html, html])
    ctx = FakeContext(page)

    # подмена внутренних ссылок на браузер/контекст (без Playwright)
    svc._browser = object()  # «как будто» есть браузер
    svc._context = ctx

    # на всякий случай убеждаемся, что детектор Cloudflare возвращает True
    assert svc._is_blocked_by_cloudflare(html) is True

    # 3 ретрая и фейл
    out = await svc.get_page_content(
        "https://example.com",
        retries=3,
        retry_delay_sec=0,
        use_stealth=False,
    )
    assert out is None
    # было 3 захода на goto
    assert page._goto_calls == 3


@pytest.mark.asyncio
async def test_http_status_retries_then_success(monkeypatch):
    """
    Сначала 429/502 → ретраим, затем 200 + обычный HTML → успех.
    """
    svc = make_service_with_fakes()

    ok_html = "<html><head><title>OK</title></head><body>All good</body></html>"
    # статусы по попыткам: 429 → 502 → 200
    page = FakePage(statuses_seq=[429, 502, 200], html_seq=["", "", ok_html])
    ctx = FakeContext(page)

    svc._browser = object()
    svc._context = ctx

    # Подстрахуемся: на «OK HTML» Cloudflare-детектор должен говорить False
    assert svc._is_blocked_by_cloudflare(ok_html) is False

    out = await svc.get_page_content(
        "https://example.com",
        retries=5,
        retry_delay_sec=0,
        use_stealth=False,
    )
    assert out == ok_html
    # было 3 захода: на двух первых статус != 200, на третьем — успех
    assert page._goto_calls == 3


@pytest.mark.asyncio
async def test_cloudflare_detector_phrases():
    """
    Юнит-тест самого детектора Cloudflare по фразам и заголовку.
    """
    svc = make_service_with_fakes()

    samples_true = [
        "<title>Just a moment...</title>",
        "Please complete the security check",
        "Verifying you are human",
        "Checking your browser before accessing",
    ]
    for s in samples_true:
        assert svc._is_blocked_by_cloudflare(s) is True

    samples_false = [
        "<title>Product page</title>",
        "Welcome to our shop",
        "",
        None,
    ]
    for s in samples_false:
        s = s or ""
        assert svc._is_blocked_by_cloudflare(s) is False