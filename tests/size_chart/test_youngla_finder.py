# tests/size_chart/test_youngla_finder.py
from bs4 import BeautifulSoup
from app.infrastructure.size_chart.youngla_finder import (
    _img_src_candidates,
    _classify,
    _normalize_url,
    YoungLASizeChartFinder,
)
from app.shared.utils.prompts import ChartType
from app.infrastructure.size_chart.table_generator_factory import CHART_TYPE_PRIORITY


def _bs(html: str):
    return BeautifulSoup(html, "html.parser")


# ─────────────────────────────────────────────────────────
# _img_src_candidates
# ─────────────────────────────────────────────────────────
def test_img_src_candidates_collects_all_basic_img_attrs():
    soup = _bs("""
        <img src="a.jpg" data-src="b.jpg" data-original="c.jpg"
             data-lazy="" data-zoom-image="d.jpg">
    """)
    img = soup.find("img")
    got = list(_img_src_candidates(img))
    assert got == ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]


def test_img_src_candidates_parses_srcset_and_data_srcset_dedup_order():
    soup = _bs("""
        <img src="fallback.jpg"
             srcset="https://cdn/x1.jpg 320w, https://cdn/x2.jpg 640w"
             data-srcset="https://cdn/x1.jpg 1x, https://cdn/x3.jpg 2x">
    """)
    img = soup.find("img")
    got = list(_img_src_candidates(img))
    # Порядок: src → srcset(каждый URL) → data-srcset(каждый URL) с дедупом
    assert got == [
        "fallback.jpg",
        "https://cdn/x1.jpg",
        "https://cdn/x2.jpg",
        "https://cdn/x3.jpg",
    ]


def test_img_src_candidates_works_with_picture_and_sources():
    soup = _bs("""
        <picture>
          <source srcset="https://cdn/hi.webp 2x, https://cdn/lo.webp 1x">
          <source data-srcset="https://cdn/alt1.jpg 1x, https://cdn/alt2.jpg 2x">
          <img src="fallback.jpg" />
        </picture>
    """)
    img = soup.find("img")
    got = list(_img_src_candidates(img))
    assert got == [
        "fallback.jpg",
        "https://cdn/hi.webp",
        "https://cdn/lo.webp",
        "https://cdn/alt1.jpg",
        "https://cdn/alt2.jpg",
    ]


# ─────────────────────────────────────────────────────────
# _normalize_url
# ─────────────────────────────────────────────────────────
def test_normalize_url_protocol_relative():
    assert _normalize_url("//cdn.example.com/a.png") == "https://cdn.example.com/a.png"


def test_normalize_url_keeps_regular_http_https():
    assert _normalize_url("http://x/a.png") == "http://x/a.png"
    assert _normalize_url("https://x/a.png") == "https://x/a.png"


# ─────────────────────────────────────────────────────────
# _classify
# ─────────────────────────────────────────────────────────
def test_classify_unique_by_url_hit():
    html = '<img src="https://cdn/site/size_chart_men.png">'
    img = _bs(html).img
    assert _classify("https://cdn/site/size_chart_men.png".lower(), img) == ChartType.UNIQUE


def test_classify_general_by_url_hit_women():
    html = '<img src="https://cdn/site/women-size-chart.png">'
    img = _bs(html).img
    assert _classify("https://cdn/site/women-size-chart.png".lower(), img) == ChartType.GENERAL


def test_classify_grid_by_url_hit():
    html = '<img src="https://cdn/site/size-grid-420.png">'
    img = _bs(html).img
    assert _classify("https://cdn/site/size-grid-420.png".lower(), img) == ChartType.UNIQUE_GRID


def test_classify_by_data_attrs_hints():
    html = '<img src="a" data-size-chart="1">'
    img = _bs(html).img
    assert _classify("a", img) == ChartType.UNIQUE

    html = '<img src="b" data-women-size="1">'
    img = _bs(html).img
    assert _classify("b", img) == ChartType.GENERAL


def test_classify_by_alt_title_fallbacks():
    img = _bs('<img src="a" alt="Men Size Chart">').img
    assert _classify("a", img) == ChartType.UNIQUE

    img = _bs('<img src="b" title="Women Size Chart">').img
    assert _classify("b", img) == ChartType.GENERAL

    img = _bs('<img src="c" alt="Size Grid for Tops">').img
    assert _classify("c", img) == ChartType.UNIQUE_GRID


# ─────────────────────────────────────────────────────────
# find_images + сортировка CHART_TYPE_PRIORITY
# ─────────────────────────────────────────────────────────
def test_find_images_collects_and_sorts_by_priority():
    html = """
    <div id="product-extra-information">
      <img src="//cdn/zzz/size_chart_top.png">         <!-- UNIQUE -->
      <img src="https://cdn/any/women-size-chart.png"> <!-- GENERAL -->
      <img src="https://cdn/x/size-grid-foo.png">      <!-- GRID -->
      <img src="https://cdn/x/not-related.png">        <!-- should be ignored -->
      <img src="https://cdn/x/size_chart_top.png"      <!-- duplicate URL -->
           srcset="https://cdn/x/size_chart_top.png 320w">
    </div>
    """
    pairs = YoungLASizeChartFinder().find_images(html)
    # ожидаемый порядок: UNIQUE (0) → GENERAL (1) → UNIQUE_GRID (2)
    assert [ctype for _, ctype in pairs] == [
        ChartType.UNIQUE, ChartType.GENERAL, ChartType.UNIQUE_GRID
    ]
    # проверим, что приоритеты действительно таковы
    assert CHART_TYPE_PRIORITY[ChartType.UNIQUE] < CHART_TYPE_PRIORITY[ChartType.GENERAL] < CHART_TYPE_PRIORITY[ChartType.UNIQUE_GRID]