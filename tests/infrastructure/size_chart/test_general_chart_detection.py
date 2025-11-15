from app.infrastructure.size_chart.general import GeneralChartVariant
from app.infrastructure.size_chart.size_chart_service import SizeChartService


def test_detects_mens_general_chart():
    url = "https://cdn.shopify.com/.../Size_Chart_TOP_JOGGER_-_Shopify.png"
    assert SizeChartService._detect_general_variant(url) is GeneralChartVariant.MEN


def test_detects_womens_general_chart():
    url = "https://cdn.shopify.com/.../YLAFH-SIZE-CHART_3.png"
    assert SizeChartService._detect_general_variant(url) is GeneralChartVariant.WOMEN
