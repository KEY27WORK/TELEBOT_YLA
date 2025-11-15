# 📐 Services — Геометрія таблиць розмірів

Модуль містить **допоміжні сервіси для розрахунку геометрії таблиць розмірів** у Telegram-боті YoungLA Ukraine.  
Він відповідає за адаптивну підгонку під розмір зображення, масштабування шрифтів і позиціонування елементів.

---

## 📂 Структура

```bash
📦 services/
├── 📘 README.md                 # цей файл: путівник по модулю
├── 📄 __init__.py               # експортує TableGeometryService
└── 📄 table_geometry_service.py # базовий сервіс обчислення геометрії
```

---

## 🧩 Залежності

- [`FontService`](../../image_generation/font_service.py) / `IFontService` — повертає шрифти та вміє міряти ширину тексту.
- [`FontType`](../../../domain/image_generation/interfaces.py) — визначає доступні типи шрифтів.

---

## 🏭 Де використовується

- `UniqueTableGenerator` (`../generators/unique_table_generator.py`) — адаптивний генератор таблиць.
- Потенційно може бути повторно використаний у майбутніх генераторах або сервісах верстки.

---

## 📌 Приклад використання

```python
from app.infrastructure.size_chart.services import TableGeometryService
from app.infrastructure.image_generation.font_service import FontService

geometry = TableGeometryService(img_width=1080, img_height=1920, padding=20)
font_service = FontService()
layout = geometry.calculate_layout(
    headers=["S", "M", "L", "XL"],
    parameters={"Груди": ["90", "100", "110", "120"]},
    base_font_size=38,
    font_service=font_service,
)
print(layout)
```

---

## 🛠 Технології

- Python 3.10+
- Pillow (ImageFont)
- PEP 8, type hints (Pyright / Pylance)

---

## 👤 Розробник

**Кирилл / @key27**  
📬 Telegram: [t.me/key27](https://t.me/key27)
