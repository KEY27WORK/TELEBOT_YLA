import pytest
from app.cores.parsers.json_ld_parser import JsonLdAvailabilityParser

def test_extract_color_size_availability_empty_html():
    html = "<html></html>"
    result = JsonLdAvailabilityParser.extract_color_size_availability(html)
    assert isinstance(result, dict)
    # В пустой странице нет цветов
    assert result == {}

def test_map_size_normalization():
    assert JsonLdAvailabilityParser._map_size("XLarge") == "XL"
    assert JsonLdAvailabilityParser._map_size("Medium") == "M"
    assert JsonLdAvailabilityParser._map_size("Unknown") == "Unknown"

def test_fallback_colors_returns_colors():
    html = """
    <div class="product-form__swatch color">
        <input name="Color" value="Red"/>
        <input name="Color" value="Blue"/>
    </div>
    """
    colors = JsonLdAvailabilityParser._fallback_colors(html)
    assert "Red" in colors
    assert "Blue" in colors
    assert colors["Red"] == {}