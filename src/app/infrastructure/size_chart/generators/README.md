# 🧱 Генератори таблиць розмірів

Модуль містить класи, що будують **PNG-таблиці розмірів** для Telegram-бота YoungLA Ukraine.  
Кожен генератор відповідає за свою схему відображення: класичну, адаптивну чи сіткову.

---

## 📂 Структура

```bash
📦 generators/
├── 📘 README.md                     # цей файл: путівник модуля
├── 📄 __init__.py                   # агрегує генератори та формує __all__
├── 🧱 base_generator.py             # базова канва, спільні утиліти та збереження PNG
├── 📋 general_table_generator.py    # класична таблиця «розмір → параметри»
├── 🖌️ unique_table_generator.py     # адаптивна таблиця з геометрією та масштабуванням
└── 🗺️ unique_grid_table_generator.py # сітка «зріст × вага → розмір»
```

| 📄 Файл                           | 🧩 Клас                     | 📌 Призначення                                      |
|----------------------------------|-----------------------------|-----------------------------------------------------|
| `base_generator.py`              | `BaseTableGenerator`        | Абстрактний клас із базовими методами (канва, текст, збереження PNG). |
| `general_table_generator.py`     | `GeneralTableGenerator`     | Класична таблиця: **розмір → параметри**.           |
| `unique_table_generator.py`      | `UniqueTableGenerator`      | Адаптивна таблиця: **параметри → розміри**, масштабує шрифти під вміст. |
| `unique_grid_table_generator.py` | `UniqueGridTableGenerator`  | Сіткова таблиця: **зріст × вага → розмір**.        |

---

## 🧩 Залежності

- [`FontService`](../image_generation/font_service.py) — надає шрифти для тексту.
- [`TableGeometryService`](../services/table_geometry_service.py) — використовується адаптивним генератором.

---

## ⚙️ Приклад використання

```python
from app.infrastructure.size_chart.generators import GeneralTableGenerator
from app.infrastructure.image_generation.font_service import FontService

font_service = FontService()
size_chart = {
    "Title": "Men's T-Shirts",
    "Розмір": ["S", "M", "L", "XL"],
    "Chest (cm)": [90, 100, 110, 120],
    "Length (cm)": [65, 68, 71, 74],
}

generator = GeneralTableGenerator(size_chart, "table.png", font_service)
await generator.generate()
print("✅ Таблиця збережена у table.png")
```

---

## 🏭 Де створюються

Генератори ініціалізуються через `TableGeneratorFactory`, яка обирає клас за `ChartType`
та проброшує `FontService`.

```python
from app.infrastructure.size_chart.table_generator_factory import TableGeneratorFactory
from app.shared.utils.prompts import ChartType

factory = TableGeneratorFactory(font_service=font_service)
generator = factory.create_generator(
    chart_type=ChartType.UNIQUE,
    data=ocr_result,
    path="table.png",
)
await generator.generate()
```

---

## 👤 Автор

**Кирилл / @key27**  
📬 Telegram: [t.me/key27](https://t.me/key27)
