from bs4 import BeautifulSoup as BS

from app.infrastructure.parsers.html_data_extractor import HtmlDataExtractor


def _make_extractor(html: str) -> HtmlDataExtractor:
    return HtmlDataExtractor(BS(html, "lxml"))


def test_extract_stock_from_mntn_payload():
    html = """
    <html><body>
    <script>
    let mntn_product_data = {
        "variants": [
            {"option1": "Black", "option2": "Small", "available": true},
            {"option1": "Black", "option2": "Medium", "available": false},
            {"option1": "Gray", "option2": "Large", "available": true}
        ]
    };
    </script>
    </body></html>
    """
    extractor = _make_extractor(html)

    assert extractor.extract_stock_from_legacy() == {
        "Black": {"Small": True, "Medium": False},
        "Gray": {"Large": True},
    }
