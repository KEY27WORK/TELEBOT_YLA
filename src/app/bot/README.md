# 🤖 bot — ядро Telegram-бота YoungLA Ukraine
Пакет **`app/bot`** містить усі шари Telegram-бота: фічі команд, обробники апдейтів, сервісний шар (`services`), UI та точку входу.

---

## 📂 Структура
```bash
bot/
├── 📘 README.md
├── 📄 __init__.py
├── 📄 main.py
├── 📂 commands
│   ├── base.py
│   ├── core_commands_feature.py
│   ├── currency_feature.py
│   ├── main_menu_feature.py
│   └── README.md
├── 📂 handlers
│   ├── callback_handler.py
│   ├── link_handler.py
│   ├── price_calculator_handler.py
│   ├── size_chart_handler_bot.py
│   ├── 📂 product
│   │   ├── collection_handler.py
│   │   ├── collection_runner.py
│   │   ├── image_sender.py
│   │   └── product_handler.py
│   └── README.md
├── 📂 services
│   ├── callback_data_factory.py
│   ├── callback_registry.py
│   ├── custom_context.py
│   ├── types.py
│   └── README.md
└── 📂 ui
    ├── static_messages.py
    ├── error_presenter.py
    ├── 📂 formatters
    ├── 📂 keyboards
    ├── 📂 messengers
    └── README.md
```

---

## 🧭 Призначення
- Оркеструвати всі Telegram-потоки: `/commands`, callback-кнопки, текстові повідомлення.
- Надавати DI-контейнер (`app.config.setup.container.Container`) і реєструвати хендлери через `BotRegistrar`.
- Інкапсулювати UI (клавіатури, форматтери, мессенджери) та статичні повідомлення.
- Визначати сервісний рівень (callback-data, CustomContext, registry), який використовують усі шари.

---

## 🧩 Компоненти
- **`main.py`** — entry-point: парсить CLI-флаги → ENV, завантажує `.env`, витягує токен, будує `Application` із `CustomContext`, реєструє хендлери, запускає `run_polling`.
- **`commands/`** — легкі фічі:
  - `base.py` — контракт `BaseFeature`.
  - `core_commands_feature.py` — `/start`, `/help`.
  - `main_menu_feature.py` — головне меню/переключення режимів.
  - `currency_feature.py` — (діючі README описують логику курсів).
- **`handlers/`** — складні обробники:
  - `link_handler.py` — маршрутизатор текстів (визначає режим, викликає обробники товару/колекцій/таблиць).
  - `callback_handler.py` — працює з `CallbackRegistry`.
  - `price_calculator_handler.py`, `size_chart_handler_bot.py` — окремі сценарії.
  - `product/` — обробка товарів і колекцій: `ProductHandler`, `CollectionHandler`, `CollectionRunner`, `ImageSender`.
- **`services/`** — сервісний шар UI:
  - `callback_data_factory.py`, `callback_registry.py`, `custom_context.py`, `types.py`, фасад у `__init__.py`.
- **`ui/`** — інтерфейс:
  - `static_messages.py`, `error_presenter.py`.
  - Підпакети `formatters`, `keyboards`, `messengers` із власними README.

---

## ⚙️ Конфігурація та контракти
- **DI/Container** (`app.config.setup.container.Container`) — створює всі залежності й передає їх у хендлери та commands.
- **ConfigService** — доступ до YAML-конфігів (`telegram.bot.token`, Playwright налаштування тощо).
- **ENV**: `BOT_TOKEN` / `TELEGRAM_BOT_TOKEN` / `TELEGRAM_TOKEN` + CLI-флаги (`--headful`, `--devtools`, `--trace`, `--channel`).
- **AppConstants** — UI тексти, callback билдєри (`CALLBACKS.*`), налаштування режимів.
- **ReasonCode + static_messages** — формування повідомлень про помилки.

---

## 🚀 Приклад запуску
```bash
python -m app.bot.main --headful --devtools
# або
BOT_TOKEN=123 python app/bot/main.py --trace=retain
```

---

## 🧪 Тестування
- Команди: мокайте `CustomContext`, перевіряйте ефекти (`reply_text`, зміна режиму).
- Хендлери: стверджуйте, що `LinkHandler`/`CallbackHandler` коректно маршрутизують, `ProductHandler` викликає потрібні сервіси.
- Services: тестуйте `CallbackData.build/parse`, `CallbackRegistry.register`, `CustomContext` getters/setters.
- UI: snapshot-тести форматтерів, перевірка клавіатур, поведінка `ImageSender` та мессенджерів.
- Entry-point: за допомогою інтеграційних тестів перевіряйте, що `build_application` додає error-handler і зберігає контейнер.

---

## ✅ Примітки
- Кожен підпакет має власний README з деталями — оновлюйте їх разом зі змінами.
- Імпортуйте компоненти через `app.bot.(commands|handlers|services|ui)` — внутрішня структура може змінюватися.
- Під час додавання нових сценаріїв не забувайте реєструвати їх у `BotRegistrar` та документувати в README.
