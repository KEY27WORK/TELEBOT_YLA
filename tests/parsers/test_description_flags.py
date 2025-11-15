import types
from app.infrastructure.parsers.html_data_extractor import HtmlDataExtractor
from bs4 import BeautifulSoup as BS

class DummyCfg:
    def __init__(self, m): self._m = m
    def get(self, key, default=None, cast=None):
        node = self._m
        for p in key.split("."):
            node = node.get(p, {})
        if node == {}:
            node = default
        return cast(node) if cast else node

def make_extractor(html="<div></div>"):
    return HtmlDataExtractor(BS(html, "lxml"))

def test_v1_path(monkeypatch):
    # форсим конфиг
    monkeypatch.setattr("app.config.config_service.ConfigService", lambda: DummyCfg({
        "flags": {"extractors": {"description": {"enabled": False}}}
    }))
    ex = make_extractor()
    ex._extract_description_v1 = types.MethodType(lambda self: "v1", ex)
    ex._extract_description_v2 = types.MethodType(lambda self: "v2", ex)
    assert ex.extract_description() == "v1"

def test_v2_forced(monkeypatch):
    monkeypatch.setattr("app.config.config_service.ConfigService", lambda: DummyCfg({
        "flags": {"extractors": {"description": {
            "enabled": True, "strategy": "v2", "rollout_percent": 0
        }}}
    }))
    ex = make_extractor()
    ex._extract_description_v1 = lambda: "v1"
    ex._extract_description_v2 = lambda: "v2"
    assert ex.extract_description() == "v2"