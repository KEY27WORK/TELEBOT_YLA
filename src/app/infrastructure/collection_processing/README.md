# ⚙️ Collection Processing

Модуль для **витягування посилань на товари зі сторінки колекції**.  
Залежить лише від контрактів домену та утиліт (`UrlParserService`), а не від конкретних реалізацій парсерів.

---

## 📂 Структура
```bash
collection_processing/
├── __init__.py
└── collection_processing_service.py
```

## 🧱 Складові

collection_processing_service.py
	•	CollectionProcessingService
Оркестратор, який:
	1.	Валідуює та нормалізує raw_url (через UrlParserService).
	2.	Перевіряє, що це справді колекційна сторінка (is_collection_url).
	3.	Створює провайдера через фабрику (IParserFactory).
	4.	Викликає provider.get_product_links().
	5.	Повертає список нормалізованих Url.

## 🚀 Використання
```python
from app.infrastructure.collection_processing import CollectionProcessingService
from app.infrastructure.parsers.factory_adapter import ParserFactoryAdapter
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.shared.utils.url_parser_service import UrlParserService

# Ініціалізація
factory = ParserFactoryAdapter(ParserFactory())
url_parser = UrlParserService(strategies=[...])
service = CollectionProcessingService(parser_factory=factory, url_parser=url_parser)

# Виклик
links = await service.get_product_links("https://youngla.com/collections/new-arrivals")
for link in links:
    print(link)
```

## ✅ Принципи
	•	Немає залежностей від конкретних парсерів (через контракт IParserFactory).
	•	Використання лише валідованих, канонічних Url.
	•	Прозоре логування ключових етапів.
	•	Граціозна обробка помилок (AppError, ParsingError).