import pytest

from app.shared.utils.size_norm import normalize_size_token


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("XSmall", "XS"),
        ("XXSmall", "XXS"),
        ("xxsmall", "XXS"),
        ("XX-Large", "XXL"),
        ("XXLarge", "XXL"),
        ("XXXSmall", "XXXS"),
        ("XXXXLarge", "XXXXL"),
    ],
)
def test_normalize_size_token_spelled_small_large_variants(raw: str, expected: str) -> None:
    assert normalize_size_token(raw) == expected
