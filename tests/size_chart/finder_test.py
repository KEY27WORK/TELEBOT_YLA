import pytest
from bs4 import BeautifulSoup

from app.infrastructure.size_chart.youngla_finder import (
    YoungLASizeChartFinder,
    _img_src_candidates,
    _classify,
    _from_srcset,
    _normalize_url,
)
from app.infrastructure.size_chart.table_generator_factory import CHART_TYPE_PRIORITY
from app.shared.utils.prompts import ChartType


# ─────────────────────────────────────────────────────────
# _from_srcset: парсинг edge-кейсов
# ─────────────────────────────────────────────────────────
def test_from_srcset_parses_all_urls():
    s1 = "https://a.example/img1.png 1x, https://b.example/img2.png 2x"
    s2 = "https://c.example/p.png 320w, https://d.example/q.png 640w , https://e 1280w"
    assert _from_srcset(s1) == ["https://a.example/img1.png", "https://b.example/img2.png"]
    assert _from_srcset(s2) == ["https://c.example/p.png", "https://d.example/q.png", "https://e"]


# ─────────────────────────────────────────────────────────
# _img_src_candidates: все источники + дедуп
# ─────────────────────────────────────────────────────────
def _mk_img(html: str):
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.select_one("img")
    assert tag is not None
    return tag

def test_img_src_candidates_collects_img_attrs_and_srcsets():
    img = _mk_img(
        """
        <img
          src="https://cdn.example/main.png"
          data-src="https://cdn.example/data.png"
          data-original="https://cdn.example/original.png"
          srcset="https://cdn.example/s1.png 320w, https://cdn.example/s2.png 640w"
          data-srcset="https://cdn.example/d1.png 1x, https://cdn.example/d2.png 2x"
        >
        """
    )
    got = list(_img_src_candidates(img))
    # порядок должен сохраняться, дубликатов нет
    assert got == [
        "https://cdn.example/main.png",
        "https://cdn.example/data.png",
        "https://cdn.example/original.png",
        "https://cdn.example/s1.png",
        "https://cdn.example/s2.png",
        "https://cdn.example/d1.png",
        "https://cdn.example/d2.png",
    ]

def test_img_src_candidates_reads_picture_sources():
    img = _mk_img(
        """
        <picture>
          <source srcset="https://a/p1.webp 1x, https://a/p2.webp 2x">
          <source data-srcset="https://a/p3.avif 1x">
          <img src="//a/fallback.jpg">
        </picture>
        """
    )
    got = list(_img_src_candidates(img))
    # из <img> + из обоих <source> (каждый url первого токена пары)
    assert got == ["//a/fallback.jpg", "https://a/p1.webp", "https://a/p2.webp", "https://a/p3.avif"]


# ─────────────────────────────────────────────────────────
# _classify: строгие хиты + эвристики alt/title/attrs
# ─────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://shop/men-size-chart.png", ChartType.UNIQUE),  # входит в UNIQUE_HITS (men-size-chart)
        ("https://shop/size_chart_top_jogger_.png", ChartType.GENERAL),  # GENERAL_HITS
        ("https://shop/grid-something.png", ChartType.UNIQUE_GRID),  # GRID_HITS
        ("https://shop/women-size-chart.png", ChartType.GENERAL),  # women → GENERAL
    ],
)
def test_classify_by_url_and_women_exclusion(url, expected):
    img = _mk_img(f'<img src="{url}">')
    assert _classify(url.lower(), img) == expected

def test_classify_by_attributes_and_alt_title():
    # data-атрибут → UNIQUE
    img1 = _mk_img('<img src="https://x/any.png" data-size-chart="1">')
    assert _classify("https://x/any.png", img1) == ChartType.UNIQUE

    # data-women-size → GENERAL
    img2 = _mk_img('<img src="https://x/any.png" data-women-size="1">')
    assert _classify("https://x/any.png", img2) == ChartType.GENERAL

    # alt/title эвристики
    img3 = _mk_img('<img src="https://x/any.png" alt="SIZE GRID overview">')
    assert _classify("https://x/any.png", img3) == ChartType.UNIQUE_GRID

    img4 = _mk_img('<img src="https://x/any.png" title="men size guide">')
    assert _classify("https://x/any.png", img4) == ChartType.UNIQUE


# ─────────────────────────────────────────────────────────
# find_images: end-to-end + сортировка по CHART_TYPE_PRIORITY
# ─────────────────────────────────────────────────────────
def test_find_images_end_to_end_and_sorting():
    html = """
    <div class="product-info__block-item">
      <!-- GENERAL: women -->
      <img src="https://cdn.shopify.com/asset/women-size-chart.png?v=1">
      <!-- UNIQUE: строгий хит -->
      <img srcset="https://cdn.shopify.com/asset/men-size-chart.png 1x, https://cdn.shopify.com/asset/men-size-chart@2x.png 2x">
      <!-- GRID: по слову grid -->
      <img data-src="https://cdn.shopify.com/asset/size-grid.png">
      <!-- шум + дубликаты -->
      <img src="//cdn.shopify.com/asset/men-size-chart.png?x=123">
    </div>
    """
    finder = YoungLASizeChartFinder()
    got = finder.find_images(html)

    # нормализация протокола // → https
    urls = [u for (u, _) in got]
    assert all(u.startswith("http") for u in urls)

    # сортировка: UNIQUE (men) → GENERAL (women) → GRID
    types = [t for (_, t) in got]
    # Проверяем стабильный порядок через таблицу приоритетов
    priority_seq = [CHART_TYPE_PRIORITY[t] for t in types]
    assert priority_seq == sorted(priority_seq)

    # Берём первый как UNIQUE (men-size-chart)
    assert got[0][1] == ChartType.UNIQUE
    # и где-то дальше есть GENERAL и GRID
    assert ChartType.GENERAL in types and ChartType.UNIQUE_GRID in types


def test_normalize_protocol_agnostic_url():
    assert _normalize_url("//cdn.example/a.png") == "https://cdn.example/a.png"
    assert _normalize_url("https://cdn.example/a.png") == "https://cdn.example/a.png"
    assert _normalize_url("") == ""