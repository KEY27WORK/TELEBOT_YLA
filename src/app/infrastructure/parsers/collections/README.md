# 📦 Parsers · `collections/`

Модуль обробляє сторінки **/collections/...** YoungLA та повертає унікальні посилання на товари для подальшої обробки доменом.

---

## 📂 Структура
```bash
collections/
├── 📘 README.md                 # (цей файл) путівник по підмодулю
├── 📄 __init__.py               # експортує UniversalCollectionParser
└── 📄 universal_collection_parser.py  # INFRA-клас парсера колекцій
```

---

## 🧭 Призначення
- Витягувати список `/products/...` URL із JSON-LD схем `ItemList/CollectionPage/SearchResultsPage`.
- Падати назад на DOM пошук із набором CSS-селекторів і пагінацією до 5 сторінок.
- Нормалізувати посилання: прибирати query/fragment, будувати абсолютні URL за базовим доменом.
- Забезпечувати єдиний вхід для оркестраторів (`ParserFactoryAdapter`) в INFRA-шарі.

---

## 🧱 Ключові файли
- **`universal_collection_parser.py`** — асинхронний парсер, що:
  - використовує `WebDriverService` для завантаження HTML (з порогом `MIN_PAGE_LENGTH_BYTES`);
  - спершу шукає JSON-LD, далі проходить DOM селектори (`PRODUCT_LINK_SELECTORS`);
  - обмежує пагінацію (`MAX_PAGINATION_PAGES = 5`) та канонізує URL через `UrlParserService`;
  - повертає `List[str]` унікальних посилань (порядок зберігається).

---

## 🚀 Приклад використання
```python
from app.infrastructure.parsers.collections import UniversalCollectionParser
from app.infrastructure.web.webdriver_service import WebDriverService
from app.config.config_service import ConfigService
from app.shared.utils.url_parser_service import UrlParserService

parser = UniversalCollectionParser(
    url="https://youngla.com/collections/men-tops",
    webdriver_service=WebDriverService(...),
    config_service=ConfigService(),
    url_parser_service=UrlParserService([...]),
)
links = await parser.get_product_links()
print(links[:3])
```

---

## 🔗 Контракти
- **Вхід:** `url: str`, `WebDriverService`, `ConfigService`, `UrlParserService`, `html_parser: str = "lxml"`.
- **Вихід:** `List[str]` — абсолютні, очищені `/products/...` URL без дублікатів.

---

## ✅ Примітки
- Це **INFRA-шар**: для домену використовуйте адаптер `ParserFactoryAdapter`, який обгортає результат у контракти `ICollectionLinksProvider`.
- Логи українською додають контекст (незавантажена колекція, порожній JSON-LD, вичерпана пагінація).
- За потреби `html_parser` і ліміти пагінації можна змінити на рівні фабрики парсерів.
