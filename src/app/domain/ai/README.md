# 🧠 Domain / AI

Домен **AI** описує *що* ми очікуємо від AI-шару через **чисті контракти** та прості DTO.  
Тут **немає** залежностей від OpenAI/Gemini SDK чи інфраструктури — лише типи та інтерфейси.  
Реалізації живуть у `infrastructure/ai` і підключаються через DI.

---

## 📁 Структура
```bash
domain/ai/
├─ init.py                  # Єдиний публічний вхід: реекспорт контрактів і DTO
├─ README.md
├─ interfaces/
│  ├─ init.py               # Локальний реекспорт типів/DTO при потребі
│  └─ prompt_service_interface.py
└─ task_contracts.py            # Контракти high-level задач: вага/переклад/слоган
```
---

## 🧱 Складові

### `interfaces/prompt_service_interface.py`
Контракт для побудови промтів (builder) + доменні DTO/Enums:

- **Контракт**
  - `IPromptService` — сервіс, що повертає **структуровані промти** для LLM.
- **DTO**
  - `ProductPromptDTO` — дані товару.
  - `ChatPrompt` — готовий промт (messages + метадані).
  - `ChatMessage` — повідомлення з роллю та мультимодальним контентом.
  - `TextPart` / `ImagePart` — типобезпечні частини повідомлення.
- **Enums/Literals**
  - `Tone` — тональність текстів.
  - `Lang` — мова.
  - `Role` — роль повідомлення (`system` | `user` | `assistant`).

> DTO і енумки — **чисті**, без згадок про конкретний провайдер (OpenAI/Gemini).

### `task_contracts.py`
Контракти для високорівневих задач (реалізуються в `infrastructure/ai`):

- `IWeightEstimator` — оцінка ваги товару (**int**, грами).
- `ITranslator` — переклад і розкладка опису по секціях (гнучкий `dict`).
- `ISloganGenerator` — генерація короткого слогану.

---

## 🔌 Контракти (приклад використання)

```python
from app.domain.ai import IWeightEstimator, ITranslator, ISloganGenerator

async def example(est: IWeightEstimator, tr: ITranslator, slog: ISloganGenerator):
    grams = await est.estimate_weight_g(
        title="YoungLA Tee",
        description="oversized cotton",
        image_url="https://..."
    )
    sections = await tr.translate_sections(text="100% cotton. Relaxed fit...")
    tagline = await slog.generate_slogan(
        title="Gladiator 4044",
        description="heavyweight, boxy fit"
    )
```

## 🧱 Побудова промтів

```python
from app.domain.ai import (
    IPromptService,
    ProductPromptDTO,
    ChatPrompt,
    Tone,
    Lang,
)

def build_prompt(service: IPromptService) -> ChatPrompt:
    dto = ProductPromptDTO(
        title="YoungLA Oversized Tee",
        description="Чорна футболка оверсайз з бавовни",
        image_url="https://..."
    )
    return service.get_slogan_prompt(dto, tone=Tone.SALES)
```

⸻

##  ✅ Принципи
	•	Чистий домен: лише інтерфейси (Protocol/ABC) і прості типи.
	•	Нуль залежностей від інфраструктури/SDK.
	•	Легка підміна реалізацій у тестах (моки/стаби).
	•	Готовність до мультимодальності (текст + зображення).
	•	Версіонування промтів через метадані ChatPrompt.

⸻