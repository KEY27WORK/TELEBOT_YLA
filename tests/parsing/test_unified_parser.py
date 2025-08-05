
import pytest
from app.cores.parsers.unified_parser import UnifiedParser

def test_parse_json_ld():
    page_source = ""  # Add mock JSON-LD content here
    result = UnifiedParser.parse_json_ld(page_source)
    assert isinstance(result, dict)


def test_format_availability():
    input_data = {"color": {"size": True}}
    result = UnifiedParser.format_availability(input_data)
    assert isinstance(result, str)

