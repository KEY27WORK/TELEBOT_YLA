# 📦 Size Chart (YoungLA Ukraine)

Інфраструктурний модуль, що вміє:
1. 🔎 знайти зображення таблиць розмірів на HTML-сторінці,  
2. ⬇️ безпечно завантажити їх з ретраями і перевіркою сигнатур,  
3. 🧾 розпізнати значення через OpenAI Vision,  
4. 🖼️ згенерувати акуратні PNG-таблиці.

---

## ⚡️ Швидкий старт

```python
from app.infrastructure.size_chart import (
    ImageDownloader, OCRService, TableGeneratorFactory,
    SizeChartService, YoungLASizeChartFinder,
)
from app.infrastructure.image_generation.font_service import FontService
from app.infrastructure.ai.open_ai_serv import OpenAIService
from app.infrastructure.ai.prompt_service import PromptService
from app.config.config_service import ConfigService

cfg = ConfigService()  # має повертати openai.api_key та моделі

downloader = ImageDownloader(max_bytes=20 * 1024 * 1024)
ocr = OCRService(
    openai_service=OpenAIService(cfg),
    prompt_service=PromptService(cfg),
)
factory = TableGeneratorFactory(font_service=FontService())
finder = YoungLASizeChartFinder()

svc = SizeChartService(
    downloader=downloader,
    ocr_service=ocr,
    generator_factory=factory,
    size_chart_finder=finder,
)

page_source = "<html>…</html>"  # HTML продукту
png_paths = await svc.process_all_size_charts(page_source)
print(png_paths)  # ["temp_size_charts/generated_0.png", ...]
```

---

## 📊 Прогрес-колбек (опційно)

```python
from app.infrastructure.size_chart.size_chart_service import Stage, SizeChartProgress

async def on_progress(p: SizeChartProgress) -> None:
    print(f"[{p.idx}] {p.stage.value} {p.url} ({p.elapsed:.2f}s) → {p.path or p.error or ''}")

svc = SizeChartService(
    downloader=downloader, ocr_service=ocr,
    generator_factory=factory, size_chart_finder=finder,
    on_progress=on_progress,
)
```

---

## ⚙️ Нюанс з типами `ChartType`

- У більшості місць ми використовуємо `app.shared.utils.prompts.ChartType`.  
- Лише в OCR-промпті потрібно передати `app.shared.utils.prompt_service.ChartType`.  

Це зроблено всередині `SizeChartService` через явний `cast`, тож ззовні нічого додатково робити не треба.

---

## 🔐 Захисти при завантаженні

- Ліміт на розмір (Content-Length + live-лічильник байтів)  
- Перевірка Content-Type (`image/*`) та магічних байтів (PNG/JPEG/GIF/WebP)  
- Атомарний запис через `*.part` + `os.replace`  
- Ретраї з псевдо-джиттером  

---

## 🖼️ Дефолтні канви

- General / Unique: **1080×1920**, padding 20  
- Grid: **1600×1200**, padding 50  

Можна перевизначити локально через `TableGeneratorFactory.create_generator(...)`.

## 📂 Структура модуля
```bash
app/infrastructure/size_chart/
├── __init__.py
├── image_downloader.py
├── ocr_service.py
├── size_chart_service.py
├── table_generator_factory.py
├── youngla_finder.py
├── generators/
│   ├── README.md
│   ├── __init__.py
│   ├── base_generator.py
│   ├── general_table_generator.py
│   ├── unique_table_generator.py
│   └── unique_grid_table_generator.py
└── services/
    ├── README.md
    ├── __init__.py
    └── table_geometry_service.py
```