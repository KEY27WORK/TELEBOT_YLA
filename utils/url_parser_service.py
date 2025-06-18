import re
from urllib.parse import urlparse

class UrlParserService:
    """
    🔗 Сервис разбора ссылок YoungLA
    """

    ALLOWED_DOMAINS = [
        "youngla.com",
        "eu.youngla.com",
        "uk.youngla.com"
    ]

    @staticmethod
    def is_allowed_domain(url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain in UrlParserService.ALLOWED_DOMAINS

    @staticmethod
    def extract_product_path(url: str) -> str:
        parsed = urlparse(url)
        match = re.search(r"/products/([^/?#]+)", parsed.path)
        if match:
            return match.group(1)
        else:
            raise ValueError("❌ Це не схоже на посилання на товар. Перевір, будь ласка.")

    @staticmethod
    def extract_collection_path(url: str) -> str:
        parsed = urlparse(url)
        match = re.search(r"/collections/([^/?#]+)", parsed.path)
        if match:
            return match.group(1)
        else:
            raise ValueError("❌ Це не схоже на посилання на колекцію. Перевір, будь ласка.")

    @staticmethod
    def is_product_url(url: str) -> bool:
        parsed = urlparse(url)
        return UrlParserService.is_allowed_domain(url) and "/products/" in parsed.path

    @staticmethod
    def is_collection_url(url: str) -> bool:
        parsed = urlparse(url)
        return UrlParserService.is_allowed_domain(url) and "/collections/" in parsed.path
