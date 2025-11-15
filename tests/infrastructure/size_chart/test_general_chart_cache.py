from pathlib import Path

from app.infrastructure.size_chart.general import GeneralChartCache, GeneralChartVariant


def test_cache_stores_and_returns_paths(tmp_path):
    cache_root = tmp_path / "cache"
    cache = GeneralChartCache(cache_root)

    assert cache.get_cached_path(GeneralChartVariant.MEN) is None

    source = tmp_path / "source.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\nmen")

    stored = cache.store_result(GeneralChartVariant.MEN, str(source))
    assert Path(stored).exists()

    cached = cache.get_cached_path(GeneralChartVariant.MEN)
    assert cached == stored


def test_cache_uses_variant_specific_files(tmp_path):
    cache = GeneralChartCache(tmp_path)

    men_png = tmp_path / "men.png"
    women_png = tmp_path / "women.png"
    men_png.write_bytes(b"men")
    women_png.write_bytes(b"women")

    cache.store_result(GeneralChartVariant.MEN, str(men_png))
    cache.store_result(GeneralChartVariant.WOMEN, str(women_png))

    assert cache.get_cached_path(GeneralChartVariant.MEN).endswith("men.png")
    assert cache.get_cached_path(GeneralChartVariant.WOMEN).endswith("women.png")
