# 🎨 Image Generation Infrastructure

Пакет `app/infrastructure/image_generation` містить сервіси, які допомагають рендерити текст у зображеннях (наприклад, для превʼю/інфографік).

---

## 📂 Структура
```bash
image_generation/
├── 📘 README.md          # (цей файл) путівник по пакетах
├── 📄 __init__.py        # експортує публічні сервіси (FontService)
└── 📄 font_service.py    # менеджер шрифтів і вимірювання тексту
```

---

## 🧱 FontService
- Читає шрифти за пріоритетом: **config → assets → системні дефолти → Pillow fallback**.
- Кешує `(FontType, size)` у памʼяті, щоб не перезавантажувати ті самі файли.
- Має допоміжний метод `get_text_width(...)` для обчислення ширини рядка.
- Логує (українською) відсутність assets, cache hit/miss і fallback-и.

### ⚙️ Конфіг
```yaml
image_generation:
  font_paths:
    bold:
      - /custom/fonts/MyBold.ttf
    mono:
      - /custom/fonts/MyMono.ttf
files:
  music_cache: music_cache
```

### 🧩 Використання
```python
from app.infrastructure.image_generation import FontService
from app.domain.image_generation.interfaces import FontType

font_service = FontService()
font = font_service.get_font(FontType.BOLD, 28)
width = font_service.get_text_width("Hello YoungLA", font)
```

---

## ✅ Переваги
- **Переносимість:** без змін працює на Linux/macOS/Windows.
- **Безпечне логування:** легкі info/debug-повідомлення допомагають знайти відсутній шрифт, але не зупиняють роботу.
- **Проста інтеграція:** імпортується з `app.infrastructure.image_generation` та впроваджується у DI як будь-який сервіс.
