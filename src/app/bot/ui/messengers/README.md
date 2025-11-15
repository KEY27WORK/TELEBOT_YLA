# ✉️ messengers — надсилання контенту в Telegram
Пакет **`app/bot/ui/messengers`** оркеструє відправку готових блоків UI: картки товарів, звіти про наявність та таблиці розмірів. Бере підготовлені дані, викликає форматтери і делегує медіа `ImageSender`/іншим сервісам.

---

## 📂 Структура
```bash
messengers/
├── 📘 README.md
├── 📄 __init__.py
├── 📄 availability_messenger.py
├── 📄 product_messenger.py
└── 📄 size_chart_messenger.py
```

- **`product_messenger.py`** — послідовно шле картку товару: фото/альбоми, опис (`MessageFormatter`), музичні рекомендації, прайс-звіт, таблицю розмірів. Використовує паузи `_BLOCK_PAUSE_SEC`, `ImageSender`, `MusicSender`, `SizeChartHandlerBot`, `ExceptionHandlerService`, `AppConstants`.
- **`availability_messenger.py`** — відправляє заголовок з посиланням, фото (якщо є) та два HTML-звіти (публічний/адмінський) на основі `ProcessedAvailabilityData`.
- **`size_chart_messenger.py`** — готує `InputFile` з PNG, делегує надсилання `ImageSender`, логічно обробляє відсутні файли і винятки.
- **`__init__.py`** — експортує `ProductMessenger`, `AvailabilityMessenger`, `SizeChartMessenger`.

---

## 🧭 Потоки
- **Product flow:** `ProcessedProductData` → форматтери/`ImageSender` → `ProductMessenger.send()` → фото → опис → прайс → музика → size-chart із retry/backoff.
- **Availability flow:** `ProcessedAvailabilityData` → `AvailabilityMessenger.send()` → HTML-підпис + фото → публічний та адмінський звіти.
- **Size chart flow:** локальні PNG → `SizeChartMessenger.send()` → підготовка `InputFile` → `ImageSender.send_images()` → fallback на текст `msg.SIZE_CHART_FAILED`.

---

## ⚙️ Конфігурація та контракти
- `AppConstants.UI.DEFAULT_PARSE_MODE`, `UI.LABELS`, `CALLBACKS.*` — визначають тексти та формат повідомлень.
- `MessageFormatter`, `PriceReportFormatter`, `ImageSender`, `MusicSender`, `SizeChartHandlerBot`, `ExceptionHandlerService` — DI-залежності, які передаються через конструктор `ProductMessenger`.
- DTO: `ProcessedProductData`, `ProcessedAvailabilityData`, шляхи до таблиць для `SizeChartMessenger`.

---

## 🚀 Приклад використання
```python
from app.bot.ui.messengers import ProductMessenger

product_messenger = ProductMessenger(
    music_sender=music_sender,
    size_chart_handler=size_chart_handler,
    formatter=message_formatter,
    image_sender=image_sender,
    exception_handler=exception_handler,
    constants=app_constants,
)

await product_messenger.send(update, context, processed_product)
```

---

## 🧪 Тестування
- Мокуйте `ImageSender.send_images` і перевіряйте, що caption/параметри передаються, а retry-логіка не дублює відправлення.
- Перевіряйте порядок викликів у `ProductMessenger.send` (фото → текст → музика → size-chart) та паузи `_BLOCK_PAUSE_SEC`.
- Для `AvailabilityMessenger` стверджуйте, що відсутність `image_url` призводить до `reply_text`, а не `reply_photo`.
- `SizeChartMessenger` — тестуйте підготовку `InputFile`, поведінку з порожнім списком файлів та делегацію виключень до `ExceptionHandlerService`.

---

## ✅ Примітки
- Всі месенджери мають працювати з уже підготовленими даними: тут немає парсингу чи OCR.
- Використовуйте `static_messages` для UX-повідомлень, не захардкожуйте рядки.
- У разі додавання нового месенджера створіть окремий файл, витягуйте залежності через конструктор і додайте його до `__init__.py` та README.
