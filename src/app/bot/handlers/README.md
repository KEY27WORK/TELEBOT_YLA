# 🤖 handlers — Telegram UI layer
Пакет **`app/bot/handlers`** — це тонкий UI-шар Telegram-бота: приймає апдейти, маршрутизує запити між режимами, делегує бізнес-логіку в домен/інфраструктуру та гарантує єдиний UX (повідомлення, прогрес, помилки).

---

## 📂 Структура
```bash
handlers/
├── 📘 README.md
├── 📄 __init__.py
├── 📄 callback_handler.py
├── 📄 link_handler.py
├── 📄 price_calculator_handler.py
├── 📄 size_chart_handler_bot.py
└── 📂 product
    ├── 📘 README.md
    ├── 📄 __init__.py
    ├── 📄 collection_handler.py
    ├── 📄 collection_runner.py
    ├── 📄 image_sender.py
    └── 📄 product_handler.py
```

---

## 🧭 Призначення
- Оркестрація всіх вхідних сценаріїв (callback, текст, URL, режими) без бізнес-логіки.
- Формування частини UX: статичні повідомлення, індикатори `ChatAction`, обробка прогресу.
- Централізований error-handling через `ExceptionHandlerService` для будь-якого handler’а.
- Координація залежностей UI рівня: `CustomContext`, `AppConstants`, Telegram bot API, інфраструктурні сервіси.
- Делегування важких задач (парсинг, OCR, pricing) у профільні сервіси з таймаутами та retry/backoff.

---

## 🧩 Компоненти
- **`__init__.py`** — зводить публічний API пакета (`CallbackHandler`, `LinkHandler`, `SizeChartHandlerBot`, `ProductHandler`, `CollectionHandler`).
- **`callback_handler.py`** — обробляє усі `callback_query`: парсить payload через `CallbackData`, кладе параметри в `context.callback_params`, шукає зареєстрований колбек у `CallbackRegistry` та делегує виконання. Весь pipeline обгорнутий у try/catch із best-effort `query.answer()`.
- **`link_handler.py`** — головний маршрутизатор тексту/URL: детектить, чи це пошук чи пряме посилання, за потреби викликає `IProductSearchProvider`, оновлює курси (`CurrencyManager`), зберігає режим у `CustomContext`, викликає режимні методи (availability/price/size) або авто-визначає продукт/колекцію через `UrlParserService`. Використовує декоратор `@product_url_required` та throttled `ChatAction`.
- **`price_calculator_handler.py`** — запускає сценарій розрахунку ціни: оновлює курси, нормалізує URL, отримує `ProductInfo` через `ParserFactory`, формує `PricingContext` із `ConfigService`, запускає синхронний розрахунок у `asyncio.to_thread` з таймаутом `LOGIC.TIMEOUTS.PRODUCT_PROCESS_SEC`, форматить відповідь через `PriceReportFormatter` і шле користувачу.
- **`size_chart_handler_bot.py`** — приймає URL/HTML, за потреби підвантажує сторінку через парсер (таймаут `_PARSER_TIMEOUT_SEC`), запускає `SizeChartService.process_all_size_charts` (таймаут `_SIZECHART_TIMEOUT_SEC`), а потім надсилає картинки через `SizeChartMessenger`. Усі Telegram-помилки ретраяться та передаються в `ExceptionHandlerService`.
- **`product/`** — підпакет UI для товарів/колекцій; див. окремий README у каталозі. Коротко:
  - **`product_handler.py`** — обробляє одиничний товар, нормалізує URL, показує регіон, викликає `ProductProcessingService` і `ProductMessenger`.
  - **`collection_handler.py`** — повністю керує флоу колекції: валідація, визначення регіону, дедуплікація посилань, ліміти `MAX_ITEMS`, прогрес, cancel за `context.mode`.
  - **`collection_runner.py`** — паралельно обробляє список URL із семафором, експоненційними ретраями, throttled прогресом та graceful cancel.
  - **`image_sender.py`** — надсилає фото/альбоми з нормалізацією медіа, chunking по 10, backoff, fallback на одиночні повідомлення.

---

## ⚙️ Конфігурація
Основні налаштування надходять із `AppConstants` + `ConfigService`. Значення читаються м’яко (відсутність блоків не ламає код).

```yaml
LOGIC:
  MODES:
    PRODUCT: product
    COLLECTION: collection
    PRICE_CALCULATION: price
    SIZE_CHART: size_chart
    REGION_AVAILABILITY: region_availability
  TIMEOUTS:
    PRODUCT_PROCESS_SEC: 55      # Таймаут розрахунку ціни
  CONVERSIONS:
    LBS_PER_KG: 2.20462          # Переведення ваги для pricing
  CURRENCY_MAP:
    USD: us
UI:
  DEFAULT_PARSE_MODE: HTML
COLLECTION:
  MAX_ITEMS: 50
  CONCURRENCY: 4
  PER_ITEM_RETRIES: 2
  PROGRESS_INTERVAL_SEC: 2.5
SENDING:
  BATCH_PAUSE_SEC: 0.4
```

`PriceCalculationHandler` додатково читає `pricing.currency_map` та `pricing.regional_costs.<region>` через `ConfigService`.

---

## 🚀 Приклад використання
```python
from telegram import Update
from app.bot.handlers import (
    CallbackHandler,
    LinkHandler,
    CollectionHandler,
    ProductHandler,
    SizeChartHandlerBot,
)
from app.bot.services.custom_context import CustomContext

# Конструюємо сервісний рівень (DI з контейнера)
callback_handler = CallbackHandler(registry, exception_handler)
product_handler = ProductHandler(...)
collection_handler = CollectionHandler(product_handler=product_handler, ...)
size_chart_handler = SizeChartHandlerBot(...)
price_handler = PriceCalculationHandler(...)
link_handler = LinkHandler(
    product_handler=product_handler,
    collection_handler=collection_handler,
    size_chart_handler=size_chart_handler,
    price_calculator=price_handler,
    availability_handler=availability_handler,
    search_resolver=search_provider,
    url_parser_service=url_parser,
    currency_manager=currency_manager,
    constants=app_constants,
    exception_handler=exception_handler,
)

async def on_text(update: Update, context: CustomContext) -> None:
    await link_handler.handle_link(update, context)

async def on_callback(update: Update, context: CustomContext) -> None:
    await callback_handler.handle(update, context)
```

---

## 🧪 Тестування
- Мокуйте `python-telegram-bot` (`Update`, `Message`, `ChatAction`, `CallbackQuery`) і перевіряйте, що без `update.message` відповіді не відправляються.
- Для `LinkHandler` підміняйте `IProductSearchProvider`, `UrlParserService` і `CurrencyManager`, щоб тестувати пошук, режими, оновлення курсів і fallback-повідомлення.
- У `PriceCalculationHandler` і `SizeChartHandlerBot` перевіряйте таймаути (`asyncio.wait_for`), обробку помилок і взаємодію з `ExceptionHandlerService`.
- Для підпакета `product/` використовуйте окремі тести на дедуплікацію URL, throttled прогрес і retry/backoff ImageSender (див. його README).

---

## ✅ Примітки
- Усі залежності інʼєктуються через конструктори — це дозволяє легко мокати сервіси та уникати глобального стану.
- `CustomContext.mode` є єдиним джерелом правди про режим; після зовнішньої зміни режиму `CollectionHandler` може зупинити довгі сценарії.
- Текстові повідомлення/шаблони мають походити з `app/bot/ui/static_messages.py`, щоб не множити «магічні рядки».
- Завжди оновлюйте README під час додавання нових режимів/handler’ів, щоб вона залишалась джерелом правди для всієї команди.
