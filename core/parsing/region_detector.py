# core/parsing/region_detector.py
import re

class RegionDetector:
    @staticmethod
    def detect_currency(url: str) -> str:
        if re.match(r"^https://(www\.)?youngla\.com/", url):
            return "USD"
        elif "eu.youngla.com" in url:
            return "EUR"
        elif "uk.youngla.com" in url:
            return "GBP"
        else:
            raise ValueError(f"❌ Невідомий регіон: {url}")
