from app.infrastructure.size_chart.general import ProductGender, YoungLAProductGenderDetector


def test_detector_returns_women_for_w_prefix():
    html = '<script type="application/ld+json">{"sku": "W345-BLK"}</script>'
    detector = YoungLAProductGenderDetector()
    assert detector.detect(html) is ProductGender.WOMEN


def test_detector_returns_men_for_numeric_sku():
    html = '<script type="application/ld+json">{"sku": "465-BLK"}</script>'
    detector = YoungLAProductGenderDetector()
    assert detector.detect(html) is ProductGender.MEN


def test_detector_returns_unknown_without_sku():
    html = "<html><head></head><body>No SKU here</body></html>"
    detector = YoungLAProductGenderDetector()
    assert detector.detect(html) is ProductGender.UNKNOWN


def test_detector_skips_numeric_candidates_until_women():
    html = """
    <script type="application/ld+json">
        {"sku": "44945940250812"}
        {"sku": "W3155-BLAK-XXS"}
    </script>
    """
    detector = YoungLAProductGenderDetector()
    assert detector.detect(html) is ProductGender.WOMEN
