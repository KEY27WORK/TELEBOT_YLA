# 🧰 Модуль `shared`

Модуль **shared** містить крос-функціональні компоненти, які використовуються у всіх шарах архітектури (`bot`, `infrastructure`, `domain`, `config`).  
Він об’єднує утиліти, сервіси та текстові шаблони, що **не належать до конкретного доменного контексту**.

---

## 📂 Структура

```bash
📦 shared/
├── 📘 README.md            # (цей файл) путівник по пакету
├── 📄 __init__.py          # опис та докстринг пакету
├── ♻️ cache/
│   ├── 📘 README.md        # опис кешуючого шару
│   ├── 📄 __init__.py      # експорт HtmlLruCache
│   └── 📄 html_lru_cache.py
├── 📊 metrics/
│   ├── 📘 README.md        # перелік метрик та експортер
│   ├── 📄 __init__.py
│   ├── 📄 content.py
│   ├── 📄 exporters.py
│   ├── 📄 ocr.py
│   └── 📄 parsing.py
├── 🧠 prompts/
│   ├── 📘 README.md        # огляд шаблонів
│   ├── 📄 __init__.py
│   ├── 🧾 ocr/
│   │   ├── 📘 README.md
│   │   ├── 📄 base.txt
│   │   ├── 📄 example_general.json
│   │   └── 📄 example_unique.json
│   └── 🇺🇦 uk/
│       ├── 📘 README.md
│       ├── 📄 alt_text.txt
│       ├── 📄 clothing_type.txt
│       ├── 📄 hashtags.txt
│       ├── 📄 music.txt
│       ├── 📄 slogan.txt
│       ├── 📄 translation.txt
│       └── 📄 weight.txt
├── 🔧 utils/
│   ├── 📘 README.md
│   ├── 📄 __init__.py
│   ├── 📄 collections.py
│   ├── 📄 immutables.py
│   ├── 📄 interfaces.py
│   ├── 📄 locale.py
│   ├── 📄 logger.py
│   ├── 📄 number.py
│   ├── 📄 prompt_loader.py
│   ├── 📄 prompt_service.py
│   ├── 📄 prompts.py
│   ├── 📄 result.py
│   ├── 📄 size_norm.py
│   └── 📄 url_parser_service.py
└── 📄 errors.py
```

---

## ✅ Призначення

- Централізація спільних сервісів (логування, промти, парсинг URL).
- Винесення текстових промтів у файли.
- Мінімізація дублювання та залежностей між модулями.
- Чистий код: SRP, KISS, ізоляція бізнес-логіки.

---

## 📚 Приклад використання

```python
from app.shared.utils import PromptService, PromptType

ps = PromptService()
prompt = ps.get_prompt(PromptType.SLOGAN, title="4044 Gladiator", description="Тканина, посадка, вайб…")
print(prompt)
```
