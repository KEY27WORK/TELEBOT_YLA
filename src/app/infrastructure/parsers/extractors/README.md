# 🧾 Пакет `extractors`

Містить міксини/утиліти для витягування даних із HTML та JSON-LD: селектори, опис, зображення, цінові блоки.

---

## 📂 Структура
```bash
📦 extractors/
├── 📘 README.md        # (цей файл)
├── 📄 __init__.py      # експортує ключові mixin-и та конфіг
├── 📄 base.py          # Selectors, _ConfigSnapshot, базові утиліти
├── 📄 description.py   # DescriptionMixin (опис, секції)
├── 📄 images.py        # ImagesMixin (головні/усі зображення)
└── 📄 json_ld.py       # JsonLdMixin (назва, опис, оффери, наявність)
```

---

## ✅ Призначення
- Уніфікувати доступ до DOM/JSON-LD без дублювання в парсерах.
- Чітко розділити відповідальність: кожний mixin відповідає за свою «зону». 
- Дати можливість збирати поведінку з міксинів (`BaseParser` просто наслідує потрібні).

---

## 🧩 Використання
```python
from app.infrastructure.parsers.extractors import (
    DescriptionMixin,
    ImagesMixin,
    JsonLdMixin,
    Selectors,
    _ConfigSnapshot,
)

class MyParser(JsonLdMixin, ImagesMixin, DescriptionMixin):
    _S = _ConfigSnapshot.selectors()
    # ... ваш код парсера
```
```
