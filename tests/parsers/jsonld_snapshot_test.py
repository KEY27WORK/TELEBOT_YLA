# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import yaml
import pytest
from bs4 import BeautifulSoup

from app.infrastructure.parsers.html_data_extractor import HtmlDataExtractor

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "jsonld"

def _build_html_with_ldjson(payload: dict) -> str:
    return f"""
    <html><head>
      <script type="application/ld+json">
      {json.dumps(payload, ensure_ascii=False)}
      </script>
    </head><body></body></html>
    """

def _collect_output(ext: HtmlDataExtractor) -> dict:
    return {
        "title": ext.extract_title(),
        "price": str(ext.extract_price()),
        "description": ext.extract_description(),
        "main_image": ext.extract_main_image(),
        "all_images": ext.extract_all_images(limit=20),
        "stock_jsonld": ext.extract_stock_from_json_ld(),
        "stock_legacy": ext.extract_stock_from_legacy(),
    }

def _load_expected(yml_path: Path) -> dict:
    with yml_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

@pytest.mark.parametrize("json_path", sorted(FIXTURES_DIR.glob("*.json")))
def test_jsonld_snapshot(json_path: Path):
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    html = _build_html_with_ldjson(payload)
    soup = BeautifulSoup(html, "html.parser")

    ext = HtmlDataExtractor(soup, locale="uk")
    got = _collect_output(ext)

    expected_path = json_path.with_suffix(".yml")
    assert expected_path.exists(), f"Создай снапшот {expected_path.name} для {json_path.name}"
    expected = _load_expected(expected_path)

    assert got == expected