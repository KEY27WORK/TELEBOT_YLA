# 📦 product — Telegram handlers (UI‑шар)
Тонкий UI-шар бота для роботи з товарами та колекціями: приймає запити користувача, робить мінімальні перевірки та делегує бізнес-логіку в сервіси домену/інфраструктури.

---

## 📂 Структура
```bash
product/
├── 📘 README.md
├── 📄 __init__.py
├── 📄 collection_handler.py
├── 📄 collection_runner.py
├── 📄 image_sender.py
└── 📄 product_handler.py
```

---

## 🧭 Призначення
- Формувати єдиний UI-потік для обробки товарів і колекцій без доменної логіки.
- Проксювати всі залежності через DI, щоб зберігати тестованість і контроль життєвого циклу.
- Забезпечувати безпечні відповіді Telegram: перевірки `update.message`, retry/backoff, централізована обробка винятків.
- Поважати обмеження платформи: ліміти на паралелізм, rate limit Telegram, throttled прогрес.
- Інкапсулювати роботу з месенджером (тексти, альбоми, fallback-повідомлення) і залишати бізнес-дані незмінними.

---

## 🧩 Компоненти
- **`__init__.py`** — експортує публічний API пакета (`ProductHandler`, `CollectionHandler`, `CollectionRunner`, `ImageSender`).
- **[`product_handler.py`](./product_handler.py)** — приймає URL товару, валідує/нормалізує через `UrlParserService`, за потреби оновлює курси (`CurrencyManager`), отримує `ProcessedProductData` та шле блоки через `ProductMessenger`.
- **[`collection_handler.py`](./collection_handler.py)** — веде повний життєвий цикл колекції: захист від порожніх апдейтів, визначення регіону, збори посилань з ретраями, дедуплікація, ліміти `MAX_ITEMS`, оновлення прогресу і cancel, якщо користувач змінив режим.
- **[`collection_runner.py`](./collection_runner.py)** — асинхронно обробляє список продуктів з семафором, експоненційними ретраями, throttled on_progress і акуратним `CancelledError`. Викликає `ProductHandler.handle_url` з `update_currency=False`, щоб не перевантажувати валютний сервіс.
- **[`image_sender.py`](./image_sender.py)** — універсальний відправник фото: нормалізує/дедуплює `str`/`InputFile`, показує `UPLOAD_PHOTO`, режисує single vs media group чанками по 10, відʼєднує довгі підписи, ретраїть `RetryAfter` і при будь-якій помилці шле UX-фолбек через `ExceptionHandlerService`.

---

## ⚙️ Конфігурація
Параметри витягуються мʼяко з `AppConstants`, тому відсутні блоки не ламають DI, але задають поведінку під час виконання.

```yaml
COLLECTION:
  MAX_ITEMS: 50                 # Верхня межа URL у запуску
  CONCURRENCY: 4                # Семафор для CollectionRunner
  PER_ITEM_RETRIES: 2           # Скільки разів ретраїмо товар
  PROGRESS_INTERVAL_SEC: 2.5    # Частота оновлень прогресу
UI:
  DEFAULT_PARSE_MODE: HTML      # Markdown/HTML для всіх службових текстів
LOGIC:
  MODES:
    COLLECTION: collection      # Значення режиму в CustomContext
SENDING:
  BATCH_PAUSE_SEC: 0.4          # Пауза між media group у ImageSender
```

---

## 🚀 Приклад використання
```python
from telegram import Update
from app.bot.handlers.product import ProductHandler, CollectionHandler
from app.bot.services.custom_context import CustomContext

product_handler = ProductHandler(
    currency_manager=currency_manager,
    processing_service=product_processing_service,
    messenger=product_messenger,
    exception_handler=exception_handler,
    constants=app_constants,
    url_parser_service=url_parser,
)

collection_handler = CollectionHandler(
    product_handler=product_handler,
    url_parser_service=url_parser,
    collection_processing_service=collection_processing_service,
    exception_handler=exception_handler,
    constants=app_constants,
)

async def product_command(update: Update, context: CustomContext) -> None:
    await product_handler.handle_url(
        update,
        context,
        url=context.args[0] if context.args else None,
    )

async def collection_command(update: Update, context: CustomContext) -> None:
    if not context.args:
        await update.message.reply_text("Очікую URL колекції")
        return
    context.url = context.args[0]
    await collection_handler.handle_collection(update, context)
```

---

## 🧪 Тестування
- Мокуйте `python-telegram-bot` (`Update`, `Message`, `ChatAction`) і стверджуйте, що повідомлення надсилаються лише після валідації.
- Підміняйте `CollectionProcessingService`/`ProductProcessingService` фікстурами, щоб перевірити дедуплікацію посилань, ліміти та error handling.
- Для `ImageSender` перевіряйте branch-логіку (single photo vs media group, детач підпису, fallback на одиночні відправки) через фейковий bot API.

---

## ✅ Примітки
- Жодного глобального стану: усі залежності прокидаються через конструктор і можуть бути замінені в тестах.
- `CollectionHandler` використовує `context.mode`, тому вище за стеком потрібно підтримувати актуальний режим бота.
- Не викликайте `handle_url` напряму в циклах без `CollectionRunner`: він сам троттлить паралелізм і розумно вимикає оновлення валют.
- `ImageSender` приховує Telegram-помилки від користувача; якщо потрібно логувати первинні причини, використовуйте `ExceptionHandlerService`.
