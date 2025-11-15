# 🔗 `infrastructure/url`

Бренд-специфічні стратегії для парсингу та нормалізації URL.  
Ці реалізації імплементують контракт `IUrlParsingStrategy` (див. `app/shared/utils/interfaces.py`) і підключаються до фасаду `UrlParserService` (у `shared`), щоб не тягнути бренд-логіку у спільний код.

---

## 🧱 Навіщо окремий шар?

- `shared` містить **абстракції** та фасади (загальні для будь-якого бренду).
- `infrastructure/url` містить **конкретні стратегії** для сайтів/брендів.
- Додаємо новий бренд → пишемо нову стратегію, не чіпаючи `shared`.

---

## 📂 Структура
```bash
📦 url/
├── 📘 README.md           # (цей файл) путівник по стратегіях
├── 📄 __init__.py         # експортує YoungLAUrlStrategy
└── 📄 youngla_strategy.py # стратегія для доменів YoungLA
```

Експортується з пакета як:

```python
from app.infrastructure.url import YoungLAUrlStrategy
```

## ⚙️ Конфіг

YoungLAUrlStrategy читає дані про регіони з ConfigService (ключ regions).
Очікується щось на кшталт:
```yaml
regions:
  usd:
    base_url: "https://youngla.com"
    currency: "USD"
  eur:
    base_url: "https://youngla.eu"
    currency: "EUR"
  gbp:
    base_url: "https://youngla.co.uk"
    currency: "GBP"
 ```

Важливо: ключі регіонів у конфігу — у нижньому регістрі (usd/eur/gbp/pln).

⸻

## 🧩 Підключення у DI / контейнері
```python
from app.shared.utils.url_parser_service import UrlParserService
from app.infrastructure.url import YoungLAUrlStrategy
from app.config.config_service import ConfigService

config = ConfigService()  # ваш спосіб ініціалізації
url_parser = UrlParserService([
    YoungLAUrlStrategy(config),
    # сюди можна додати інші стратегії у майбутньому
])
```

## 🧪 Приклади використання
```python
url = "https://youngla.com/products/4044-gladiator"

url_parser.is_product_url(url)        # True
url_parser.is_collection_url(url)     # False
url_parser.extract_product_slug(url)  # "4044-gladiator"
url_parser.get_currency(url)          # "USD"
url_parser.get_region_label(url)      # "US 🇺🇸"

# Побудова лінку на товар для іншого регіону:
url_parser.build_product_url("eur", "4044-gladiator")
# -> "https://youngla.eu/products/4044-gladiator"
```

## ➕ Додавання нового бренду
	1.	Створіть newbrand_strategy.py у цій директорії.
	2.	Імплементуйте IUrlParsingStrategy (supports/is_product_url/…).
	3.	Додайте стратегію у список при створенні UrlParserService.
