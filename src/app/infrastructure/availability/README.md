# 🌍 infrastructure/availability
Інфраструктурний шар, який перевіряє наявність товарів у різних регіонах і формує готові звіти для Telegram.

---

## 📂 Структура
```
availability/
├── 📘 README.md
├── 📄 __init__.py
├── 📄 availability_processing_service.py
├── 📄 availability_manager.py
├── 📄 cache_service.py
├── 📄 dto.py
├── 📄 formatter.py
├── 📄 report_builder.py
├── 📄 metrics.py
├── 📄 availability_handler.py
└── 📄 availability_i18n.py
```

---

## 🧭 Призначення
- Приймати посилання від користувача й оркеструвати повний сценарій: URL → slug → заголовок + звіт.  
- Кешувати результати перевірок і вести Prometheus-метрики (cache hit/miss, latency).  
- Форматувати дані про наявність у вигляді кольорів/розмірів, готових до відправлення в Telegram.  
- Надати локалізовані повідомлення (uk/ru/en) для хендлера та месенджера.  
- Інкапсулювати роботу з parser factory та налаштуваннями регіонів у одному місці.

---

## 🧩 Ключові компоненти
- **`availability_handler.py`** — точка входу Telegram-бота; визначає мову, викликає `AvailabilityProcessingService` і надсилає відповіді.  
- **`availability_processing_service.py`** — перетворює URL на slug, будує заголовок (`ProductHeaderDTO`) і викликає `AvailabilityManager`; контролює таймаут.  
- **`availability_manager.py`** — паралельно опитує регіони, кешує результати, знімає метрики промахів/хітів.  
- **`cache_service.py`** — потокобезпечний TTL-кеш із опційною файловою персистенцією, статистикою та евікціями.  
- **`report_builder.py` / `formatter.py`** — конвертують карти кольорів/розмірів у текстові блоки, окремо для публічного та адмінського звіту.  
- **`dto.py`** — `AvailabilityReports` та похідні DTO, які передаються в бот.  
- **`metrics.py`** — лічильники Prometheus: `availability_cache_hits_total`, `availability_cache_misses_total`, `availability_report_seconds`.  
- **`availability_i18n.py`** — локалізація службових повідомлень (`t`, `normalize_lang`).  
- **`__init__.py`** — експортує публічний API (`AvailabilityHandler`, `AvailabilityManager`, `AvailabilityCacheService`, `AvailabilityReports`, локалізацію).

---

## 🔄 Потік
1. `AvailabilityHandler` отримує URL від користувача й визначає локаль.  
2. `AvailabilityProcessingService` нормалізує URL → slug, будує заголовок та викликає `AvailabilityManager`.  
3. `AvailabilityManager` тягне дані для всіх регіонів, кешує результати, передає їх у `ReportBuilder`.  
4. `ReportBuilder` + `formatter.py` формують текстові блоки (колір/розмір, підсумок).  
5. `AvailabilityMessenger` (за межами каталогу) відправляє `AvailabilityReports` користувачу.

---

## 🚀 Приклад використання
```python
from app.infrastructure.availability import (
    AvailabilityHandler,
    AvailabilityProcessingService,
    AvailabilityManager,
    AvailabilityCacheService,
)
from app.bot.ui.messengers.availability_messenger import AvailabilityMessenger
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.domain.availability.services import AvailabilityService

manager = AvailabilityManager(
    availability_service=AvailabilityService(...),
    parser_factory=ParserFactory(...),
    cache_service=AvailabilityCacheService(max_items=512),
    report_builder=...,
    config_service=...,
    url_parser_service=...,
)
processing = AvailabilityProcessingService(
    manager=manager,
    header_service=...,
    url_parser_service=...,
    config=...,
)
handler = AvailabilityHandler(
    processing_service=processing,
    messenger=AvailabilityMessenger(...),
)

await handler.handle_price_availability(update, context, url="https://shop.example/item")
```

---

## ✅ Примітки
- Якщо додаєш новий формат звіту, онови `report_builder.py` та README, щоб він відображався у «Ключових компонентах».  
- TTL/конфіг кешу зчитуються через `ConfigService`: якщо міняєш ключі в YAML — синхронізуй із `availability_manager.py`.  
- Метрики з `metrics.py` реєструються під префіксом `availability_*`; не забувай додавати їх у Prometheus manifests.  
- Локалізація (`availability_i18n.py`) — єдине джерело текстів для handler/messenger; не дублюй рядки у коді.
