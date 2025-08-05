# 🔗 app/shared/utils/url_parser_service.py
"""
🔗 url_parser_service.py — Єдиний сервіс для розбору та валідації URL.

🔹 Клас `UrlParserService`:
- Визначає, чи є URL посиланням на товар або колекцію.
- Витягує валюту, регіон, базовий домен з конфігурації.
- Парсить частини URL (наприклад, назву товару).
- Використовує ConfigService як єдине джерело правди про регіони.
"""

# 🔠 Системні імпорти
import re                                                  # 🔤 Регулярні вирази для парсингу
from typing import Optional, Dict, Any                     # 🧰 Типізація
from urllib.parse import urlparse                          # 🌐 Парсинг URL

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService        # ⚙️ Конфігурація регіонів і базових URL


# ================================
# 🏛️ КЛАС СЕРВІСУ РОЗБОРУ URL
# ================================
class UrlParserService:
    """
    ⚙️ Надає повний набір інструментів для роботи з URL-адресами YoungLA.
    """

    def __init__(self, config_service: ConfigService):
        """
        ⚙️ Ініціалізує сервіс та кешує дані про регіони з конфігурації.
        """
        self._config = config_service                                                   # ⚙️ DI конфігурації
        self._regions_data: Dict[str, Any] = self._config.get("regions", {})            # 🌍 Дані про всі регіони
        self._domains = {
            self._normalize_domain(data.get("base_url", ""))
            for data in self._regions_data.values()
            if data.get("base_url")
        }                                                                               # 🌐 Сет нормалізованих доменів

    # ================================
    # 🌍 ПУБЛІЧНІ МЕТОДИ ДЛЯ РОБОТИ З РЕГІОНАМИ
    # ================================

    def get_currency(self, url: str) -> str:
        """
        💰 Визначає валюту (USD, EUR, GBP) на основі домену в URL.

        Returns:
            str: Код валюти.
        Raises:
            ValueError: Якщо регіон не вдалося визначити.
        """
        normalized_url_domain = self._normalize_domain(url)                             # 🌐 Витягуємо домен із URL
        for region_code, region_data in self._regions_data.items():
            base_domain = self._normalize_domain(region_data.get("base_url", ""))
            if normalized_url_domain == base_domain:
                return region_data.get("currency")                                      # ✅ Знайдено відповідність

        raise ValueError(f"❌ Не вдалося визначити валюту для URL: {url}")              # ❌ Не знайдено регіон

    def get_region(self, url: str) -> str:
        """
        🌍 Повертає назву регіону з прапором (напр., "US 🇺🇸").
        """
        currency = self.get_currency(url)                                               # 💱 Спершу визначаємо валюту
        return {
            "USD": "US 🇺🇸",
            "EUR": "EU 🇪🇺",
            "GBP": "UK 🇬🇧"
        }.get(currency, "Unknown")                                                      # 📦 Маппінг до назви регіону

    def get_base_url(self, currency: str) -> str:
        """
        🌐 Повертає базовий URL для заданої валюти.
        """
        key = f"regions.{currency.lower()}.base_url"                                    # 🗝️ Побудова ключа до конфігурації
        return self._config.get(key, "https://www.youngla.com")                         # 🔁 Fallback URL

    def build_product_url(self, region_code: str, product_path: str) -> Optional[str]:
        """
        🏗️ Будує повний URL товару для конкретного регіону.
        """
        base_url = self._regions_data.get(region_code, {}).get("base_url")               # 🌐 Отримуємо базовий URL з кешованих даних
        if not base_url:
            return None
        return f"{base_url}{product_path}"                                              # 🔗 Склеюємо URL

    # ================================
    # 🧐 ПУБЛІЧНІ МЕТОДИ ДЛЯ АНАЛІЗУ URL
    # ================================

    def is_product_url(self, url: str) -> bool:
        """🛍️ Перевіряє, чи є посилання URL-адресою товару."""
        return self._is_valid_domain(url) and "/products/" in urlparse(url).path

    def is_collection_url(self, url: str) -> bool:
        """📚 Перевіряє, чи є посилання URL-адресою колекції."""
        return self._is_valid_domain(url) and "/collections/" in urlparse(url).path

    def extract_product_slug(self, url: str) -> Optional[str]:
        """🧩 Витягує частину URL, що ідентифікує товар (slug)."""
        match = re.search(r"/products/([^/?#]+)", urlparse(url).path)
        return match.group(1) if match else None                                        # 🧠 Якщо знайдено — повертаємо slug

    # ================================
    # 🕵️‍♂️ ПРИВАТНІ ДОПОМІЖНІ МЕТОДИ
    # ================================

    def _is_valid_domain(self, url: str) -> bool:
        """🌍 Перевіряє, чи належить домен до дозволеного списку."""
        return self._normalize_domain(url) in self._domains                             # ✅ Порівняння з whitelist

    def _normalize_domain(self, url_or_domain: str) -> str:
        """
        🧹 Приводить домен до єдиного формату (без 'www.' та 'https://').
        """
        if "https://" in url_or_domain or "http://" in url_or_domain:
            domain = urlparse(url_or_domain).netloc
        else:
            domain = url_or_domain

        return domain.lower().replace("www.", "")                                       # 🧼 Видаляємо www та знижуємо регістр
