import os
from contextlib import contextmanager
from app.infrastructure.parsers._infra_options import ParserInfraOptions

@contextmanager
def _env(**pairs):
    old = {k: os.environ.get(k) for k in pairs}
    try:
        for k, v in pairs.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(v)
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

def test_defaults_when_env_empty():
    with _env(
        PARSER_HTML_PARSER=None,
        PARSER_REQUEST_TIMEOUT_SEC=None,
    ):
        opts = ParserInfraOptions.from_env()
        assert opts.html_parser == "lxml"
        assert opts.request_timeout_sec == 30

def test_override_with_default_prefix():
    with _env(PARSER_REQUEST_TIMEOUT_SEC="7", PARSER_IMAGES_LIMIT="35"):
        opts = ParserInfraOptions.from_env()
        assert opts.request_timeout_sec == 7
        assert opts.images_limit == 35

def test_custom_prefix_yla_parser():
    with _env(
        YLA_PARSER_REQUEST_TIMEOUT_SEC="11",
        YLA_PARSER_FILTER_SMALL_IMAGES="0",
        PARSER_REQUEST_TIMEOUT_SEC=None,
        PARSER_FILTER_SMALL_IMAGES=None,
    ):
        opts = ParserInfraOptions.from_env(prefix="YLA_PARSER_")
        assert opts.request_timeout_sec == 11
        assert opts.filter_small_images is False

def test_invalid_values_fall_back_to_defaults():
    with _env(PARSER_IMAGES_LIMIT="-999", PARSER_RETRY_ATTEMPTS="-1"):
        # from_env не бросает — __post_init__ валидирует и сохранит дефолты
        opts = ParserInfraOptions.from_env()
        assert opts.images_limit == 30
        assert opts.retry_attempts == 3
        