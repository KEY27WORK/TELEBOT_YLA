# 🔗 app/infrastructure/url/youngla_strategy.py
"""
🔗 `YoungLAUrlStrategy` — брендова стратегія парсингу URL для YoungLA.

🔹 Працює лише з доменами, оголошеними у конфігурації `regions`.
🔹 Визначає валюту та «людську» назву регіону (label) за доменом.
🔹 Сумісна з протоколом `IUrlParsingStrategy` (контракт пакету `shared.utils`).
🔹 Керує кешами в межах процесу, щоб пришвидшити повторні виклики.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import re                                             # 🧵 Робота з шаблонами шляху
from typing import Any, Dict, Iterable, Optional      # 🧰 Анотації типів
from urllib.parse import urlparse                     # 🌐 Нормалізація URL

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService   # ⚙️ Доступ до конфігурації
from app.shared.utils.interfaces import IUrlParsingStrategy  # 🔗 Контракт стратегії

__all__ = ["YoungLAUrlStrategy"]


# ================================
# 🧱 ВНУТРІШНІ КОНСТАНТИ
# ================================
_DEFAULT_REGION_LABELS: Dict[str, str] = {
    "USD": "US 🇺🇸",
    "EUR": "EU 🇪🇺",
    "GBP": "UK 🇬🇧",
    "PLN": "PL 🇵🇱",
}  # 🧭 Фолбек, якщо labels не задані


# ================================
# 🔗 СТРАТЕГІЯ ДЛЯ YOUNGLA
# ================================
class YoungLAUrlStrategy(IUrlParsingStrategy):
    """Реалізація контракту `IUrlParsingStrategy` для бренду YoungLA."""

    def __init__(self, config: ConfigService) -> None:
        self._cfg = config                                                       # ⚙️ Джерело конфігурації
        self._regions: Dict[str, Any] = self._cfg.get("regions") or {}           # 🌍 Вузол `regions.*`

        raw_labels = self._cfg.get("regions.labels")                             # 🏷️ Кастомні підписи регіонів
        self._region_labels: Dict[str, str] = (
            raw_labels if isinstance(raw_labels, dict) else {}
        ) or dict(_DEFAULT_REGION_LABELS)

        # 📌 Дозволені кореневі домени (без www і порта)
        self._allowed_roots: set[str] = {
            self._norm_domain(region.get("base_url", ""))                        # 🔄 Нормалізуємо домен
            for region in self._regions.values()
            if isinstance(region, dict) and region.get("base_url")
        }

        # 🗂️ Мапа root-домен → вузол конфігурації
        self._root_to_region: Dict[str, Dict[str, Any]] = {}
        for region_node in self._regions.values():                                    # 🔁 Обходимо всі конфіг-рядки
            if not isinstance(region_node, dict):                                     # 🛑 Пропускаємо некоректні вузли
                continue
            root = self._norm_domain(region_node.get("base_url", ""))                 # 🧮 Нормалізуємо базовий домен
            if root:
                self._root_to_region[root] = region_node                               # 🗺️ Прив'язуємо домен до вузла

        # 🔒 In-memory кеші (процесні)
        self._currency_cache: Dict[str, Optional[str]] = {}                      # домен → валюта
        self._label_cache: Dict[str, str] = {}                                   # домен → label

    # ================================
    # IUrlParsingStrategy
    # ================================
    def supports(self, domain: str) -> bool:
        """True, якщо домен належить YoungLA (root або сабдомен)."""
        normalized = self._norm_domain(domain)                                   # 🧮 Приводимо домен до канону
        if not normalized or not self._allowed_roots:
            return False
        return self._is_same_or_subdomain(normalized, self._allowed_roots)

    def get_currency(self, url: str) -> Optional[str]:
        """Повертає валюту (USD/EUR/GBP/PLN) для переданого URL."""
        normalized = self._norm_domain(url)                                      # 🧮 Витягуємо домен
        if not normalized:
            return None
        if normalized in self._currency_cache:                                   # ⚡ Кешований результат
            return self._currency_cache[normalized]
        root = self._match_root(normalized, self._allowed_roots)                 # 🧭 Шукаємо відповідний root
        if not root:
            self._currency_cache[normalized] = None
            return None
        region_node = self._root_to_region.get(root) or {}                      # 🗺️ Вузол конфігурації для кореня
        currency = region_node.get("currency")                                  # 💱 Код валюти, якщо заданий
        self._currency_cache[normalized] = currency                             # 💾 Кешуємо результат
        return currency

    def get_region_label(self, url: str) -> str:
        """Повертає label (з прапорцем) для регіону або `"Unknown"`."""
        normalized = self._norm_domain(url)                                      # 🧮 Витягуємо домен
        if not normalized:
            return "Unknown"
        if normalized in self._label_cache:                                      # ⚡ Кешований label
            return self._label_cache[normalized]
        currency = self.get_currency(url)
        label = self._region_labels.get(currency or "", "Unknown")               # 🪪 Підпис для валюти
        self._label_cache[normalized] = label
        return label

    def get_base_url(self, currency: str) -> Optional[str]:
        """Повертає базовий URL (із конфігу) для заданої валюти."""
        if not currency:
            return None
        region_node = self._regions.get(currency.lower())                       # 🗺️ Вузол, де описаний регіон
        return (region_node or {}).get("base_url")                              # 🌐 Базовий домен для побудови URL

    def build_product_url(self, region_code: str, product_path: str) -> Optional[str]:
        """Будує повне посилання на товар за кодом регіону та шляхом."""
        if not region_code or not product_path:
            return None
        region_node = self._regions.get(region_code.lower())                    # 🗺️ Шукаємо конфігурацію регіону
        base_url = (region_node or {}).get("base_url")                          # 🌐 Базовий URL із конфігу
        if not base_url:
            return None
        return f"{base_url.rstrip('/')}/products/{product_path.lstrip('/')}"

    def is_product_url(self, url: str) -> bool:
        """True, якщо посилання вказує на сторінку товару YoungLA."""
        return self._belongs_to_brand(url) and "/products/" in (urlparse(url).path or "")

    def is_collection_url(self, url: str) -> bool:
        """True, якщо посилання вказує на сторінку колекції YoungLA."""
        return self._belongs_to_brand(url) and "/collections/" in (urlparse(url).path or "")

    def extract_product_slug(self, url: str) -> Optional[str]:
        """Видобуває slug товару зі шляху `/products/...`."""
        path = urlparse(url).path or ""
        match = re.search(r"/products/([^/?#]+)", path)                         # 🧵 Пошук фрагменту між `/products/` і кінцем
        return match.group(1) if match else None

    # ================================
    # 🔧 ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _belongs_to_brand(self, url_or_domain: str) -> bool:
        """True, якщо переданий URL/домен належить до дозволених root-доменів."""
        normalized = self._norm_domain(url_or_domain)                            # 🧮 Нормалізуємо введення
        if not normalized:
            return False
        return self._is_same_or_subdomain(normalized, self._allowed_roots)

    @staticmethod
    def _norm_domain(url_or_domain: str) -> str:
        """Нормалізує URL/домен: прибирає протокол, `www.` та порт."""
        if not url_or_domain:                                                   # 🛑 Порожній ввід → повертаємо пустий рядок
            return ""
        domain = (
            urlparse(url_or_domain).netloc if "://" in url_or_domain else url_or_domain
        )  # 🔍 Якщо передали URL — витягуємо netloc
        domain = (domain or "").strip().lower()                                 # 🧽 Прибираємо пробіли та знижуємо регістр
        if domain.startswith("www."):                                           # 🪄 Прибираємо префікс www.
            domain = domain[4:]
        if ":" in domain:                                                       # 🔪 Усуваємо порт (":443")
            domain = domain.split(":", 1)[0]
        return domain

    @staticmethod
    def _is_same_or_subdomain(domain: str, roots: Iterable[str]) -> bool:
        """Перевіряє, чи дорівнює `domain` одному з roots або є його сабдоменом."""
        return any(                                                             # 🔁 Шукаємо збіг із root або сабдоменом
            domain == root or domain.endswith("." + root) for root in roots
        )

    @staticmethod
    def _match_root(domain: str, roots: Iterable[str]) -> Optional[str]:
        """Повертає root-домен, якому належить `domain` (якщо знайдено)."""
        for root in roots:                                                      # 🔁 Обходимо всі дозволені домени
            if domain == root or domain.endswith("." + root):                   # ✅ Повертаємо перший відповідний root
                return root
        return None


# ================================
# 🧩 ПРИКЛАД НАЛАШТУВАНЬ У CONFIG
# ================================
# regions:
#   us:
#     base_url: "https://www.youngla.com"
#     currency: "USD"
#   eu:
#     base_url: "https://eu.youngla.com"
#     currency: "EUR"
#   uk:
#     base_url: "https://uk.youngla.com"
#     currency: "GBP"
#   labels:
#     USD: "США 🇺🇸"
#     EUR: "ЄС 🇪🇺"
#     GBP: "Британія 🇬🇧"
