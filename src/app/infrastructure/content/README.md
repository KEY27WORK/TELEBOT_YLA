# 🧠 Infrastructure · Content

Інфраструктурні сервіси для текстового/медійного контенту товарів YoungLA.

---

## 📂 Структура
```bash
content/
├── 📘 README.md                 # (цей файл) путівник каталогу
├── 📄 __init__.py               # експортує публічні сервіси/DTO
├── 📄 alt_text_generator.py     # ALT-тексти (OpenAI + кеш)
├── 📄 gender_classifier.py      # Гендерні теги за артикулом
├── 📄 hashtag_generator.py      # Генерація хештегів (конфіги + AI)
├── 📄 product_content_service.py # Оркестратор повного контенту
└── 📄 product_header_service.py # Легкі заголовки (title + hero + url)
```

---

## 🧭 Призначення
- Формувати контент товару для бота: слоган, перекладені секції, хештеги, ціни, ALT.
- Витягувати компактні заголовки без повного пайплайна парсингу.
- Узгоджувати доменні контракти (`IHashtagGenerator`, `ITextAI`) з інфраструктурними реалізаціями.
- Надавати адаптери (`HashtagGeneratorStringAdapter`, `PriceMessageFacade`) для сумісності зі старим кодом.

---

## 🧱 Ключові файли
- **`alt_text_generator.py`** — асинхронно генерує ALT-тексти (OpenAI + HtmlLruCache + метрики).
- **`gender_classifier.py`** — повертає хештеги за префіксом артикула (з fallback `default`).
- **`hashtag_generator.py`** — комбінує базові теги, гендерні правила, AI-відповідь і санітизацію → `Set[str]`.
- **`product_content_service.py`** — агрегує все в `ProductContentDTO` (переклад, слоган, хештеги, PriceFacade, ALT).
- **`product_header_service.py`** — швидко витягує title + main image + canonical URL через `ParserFactory`.

---

## 🚀 Приклад використання
```python
from app.config.config_service import ConfigService
from app.infrastructure.content import (
    ProductContentService,
    ProductHeaderService,
)
from app.infrastructure.adapters import HashtagGeneratorStringAdapter, PriceMessageFacade

config = ConfigService()
content_service = ProductContentService(
    translator=my_translator,
    hashtag_generator=my_hashtag_generator,
    price_handler=my_price_handler,
    alt_text_generator=my_alt_generator,
)

header_service = ProductHeaderService(parser_factory, url_parser_service)
dto = await content_service.build_product_content(product_info, url=product_url, colors_text="...")
header = await header_service.create_header("products/4044-gladiator", region="us")
```

---

## ⚙️ Конфігурація
- `hashtags.base` — список базових тегів.
- `currency_api.*` — для PriceCalculationHandler/Facade (щоб зібрати `price_message`).
- `gender_rules` — карта префікс → теги (інʼєктується у `GenderClassifier`/`HashtagGenerator`).
- `.env` / OpenAI — ключі для `AltTextGenerator` та укр. промптів.

---

## ✅ Примітки
- Усі сервіси логують ключові кроки (успіхи/помилки) згідно зі STYLEGUIDE.
- `__init__.py` переекспортує `ProductContentService`, `ProductHeaderService`, DTO й адаптери для DI-контейнера.
- `alt_text_generator.py` використовує best-effort підхід: збої не блокують побудову контенту.
