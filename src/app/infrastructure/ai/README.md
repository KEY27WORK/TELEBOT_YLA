# 🧠 infrastructure/ai
Інфраструктурний шар для роботи з LLM: приймає доменні DTO, формує промпти та викликає OpenAI без бізнес-логіки.

---

## 📂 Структура
```
ai/
├── 📘 README.md
├── 📄 __init__.py
├── 📄 ai_task_service.py
├── 📄 dto.py
├── 📄 open_ai_serv.py
├── 📄 prompt_service.py
└── 📄 telemetry_ai.py
```

---

## 🧭 Призначення
- Інкапсулювати виклики OpenAI (chat + vision) та приховати SDK за стабільними контрактами.
- Надавати домену чисті DTO (`ChatPrompt`, `ProductInfo`, `FullPriceDetails`) без Telegram/UI залежностей.
- Реалізовувати доменні інтерфейси `IWeightEstimator`, `ITranslator`, `ISloganGenerator`.
- Писати телеметрію про вартість/довжину запитів та кешувати переклади.
- Уніфікувати промпти: температура/`max_tokens` беруться з конфіга, мова відповіді задається централізовано.

---

## 🧩 Ключові компоненти
- **`dto.py`** — `Role`, `ChatMessage`, `ChatPrompt`; логують створення, щоб відстежувати побудову промптів.  
- **`prompt_service.py`** — формує `ChatPrompt` зі спільного PromptBuilder, застосовує overrides із конфіга, додає system-msg про мову.  
- **`open_ai_serv.py`** — асинхронний клієнт OpenAI: конвертує DTO у формат API, підтримує vision, логує параметри та помилки.  
- **`telemetry_ai.py`** — `TelemetrySink` і `AITelemetry`: маскування інпутів, оцінка вартості, JSONL-запис подій.  
- **`ai_task_service.py`** — сервіс задач (вага, переклад, слоган) із TTL-кешем, телеметрією та fallback-логікою.  
- **`__init__.py`** — експортує публічний API (`AITaskService`, `PromptService`, `OpenAIService`, DTO).

---

## ⚙️ Конфігурація
```yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini
  vision_model: gpt-4o-mini
  defaults:
    temperature: 0.3
    max_tokens: 1024
  prompts:
    slogan:
      temperature: 0.7
      max_tokens: 64
    translation:
      temperature: 0.3
      max_tokens: 1024
    weight:
      temperature: 0.2
      max_tokens: 32
    hashtags:
      temperature: 0.5
      max_tokens: 128
    size_chart:
      temperature: 0.0
      max_tokens: 2048
openai.cache:
  enabled: true
  ttl_hours: 720
  max_items: 1000
  persist_dir: var/cache/openai_translations
```

```bash
# .env
OPENAI_API_KEY=sk-xxx
```

---

## 🚀 Приклад використання
```python
from app.config.config_service import ConfigService
from app.infrastructure.ai import AITaskService, OpenAIService, PromptService

cfg = ConfigService()
openai_client = OpenAIService(cfg)
prompt_builder = PromptService(cfg)
ai_tasks = AITaskService(openai_client, prompt_builder)

# ⚖️ Вага
grams = await ai_tasks.estimate_weight_g(
    title="YoungLA Tee",
    description="oversized cotton",
    image_url="https://cdn.example.com/1.png",
)

# 🌐 Переклад
sections = await ai_tasks.translate_sections(text="100% cotton. Relaxed fit...")

# ✨ Слоган
slogan = await ai_tasks.generate_slogan(
    title="Gladiator 4044",
    description="heavyweight, boxy fit",
)
```

---

## ✅ Примітки
- У `open_ai_serv.py` та `dto.py` використані `cast(...)` + логування, щоб Pylance не скаржився на `ChatCompletionMessageParam`.  
- `TelemtrySink` пише JSONL у `var/telemetry/ai.jsonl` і дублює події в лог — не забудьте про ротацію.  
- `ai_task_service.py` має дисковий TTL-кеш для перекладів; якщо змінюєте схему кешу — почистіть `persist_dir`.  
- Для тестів мокайте `OpenAIService` або `TelemetrySink` — контракти домену залишаються незмінними.
