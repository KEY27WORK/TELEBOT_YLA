"""
🧪 test_json_ld_parser.py — unit-тести для JsonLdAvailabilityParser

Перевіряє:
- Парсинг JSON-LD блоку з HTML
"""

from core.parsers.json_ld_parser import JsonLdAvailabilityParser  # 🧠 Парсер JSON-LD блоків

def test_parse_availability_basic():
    parser = JsonLdAvailabilityParser()

    # 🧾 HTML, що містить JSON-LD з офферами
    html = """
    <html><head></head><body>
    <script type="application/ld+json">
    {
        "@type": "Product",
        "offers": [
            {
                "name": "Black / Large",
                "availability": "http://schema.org/InStock"
            },
            {
                "name": "Black / Medium",
                "availability": "http://schema.org/OutOfStock"
            },
            {
                "name": "White / Small",
                "availability": "http://schema.org/InStock"
            }
        ]
    }
    </script>
    </body></html>
    """

    # 📤 Парсимо й очікуємо правильну структуру
    result = parser.extract_color_size_availability(html)
    assert result == {
        "Black": {"L": True, "M": False},
        "White": {"S": True}
    }

