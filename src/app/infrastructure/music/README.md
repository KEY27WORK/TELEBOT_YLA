# 🎵 Infrastructure: Music

Підсистема роботи з музикою у **TELEBOTYLAUKRAINE**.  
Забезпечує інтеграцію з AI та YouTube для підбору і надсилання треків у Telegram.

---

## 📂 Структура

```bash
music/
├── __init__.py              # Ініціалізація пакету (експортує ключові сервіси)
├── music_sender.py          # Оркестратор: надсилає список + треки у фоні
├── music_recommendation.py  # Підбір треків через AI (IMusicRecommender)
├── music_file_manager.py    # Файловий кеш для mp3 (IMusicFileManager)
└── yt_downloader.py         # Завантаження треків з YouTube (IMusicDownloader)
```

---

## 📌 Призначення

- **MusicRecommendation** — звертається до OpenAI, будує список `RecommendedTrack`.
- **YtDownloader** — качає аудіо з YouTube у форматі mp3, збереження у кеш.
- **MusicFileManager** — керує локальним кешем (шляхи, очищення).
- **MusicSender** — повний UX-сценарій у боті: від списку до відправки аудіо.

---

## 🔗 Контракти

Усі сервіси реалізують **доменні інтерфейси** з `app/domain/music/interfaces.py`:

- `IMusicRecommender.recommend(product: ProductPromptDTO) -> MusicRecommendationResult`
- `IMusicDownloader.download(track: RecommendedTrack) -> TrackInfo`
- `IMusicFileManager.get_cached_path(track: RecommendedTrack) -> Optional[str]`

---

## ⚙️ Конфігурація (ConfigService)

Ключові параметри у `config/yamls/*.yaml`:

```yaml
music:
  recommendation:
    model: gpt-4o-mini
    temperature: 0.7
  download:
    socket_timeout: 15
    retries: 3
    fragment_retries: 3
    concurrent_fragments: 4
    mp3_bitrate_kbps: 192
    concurrent_downloads: 3
  send:
    concurrent_sends: 3
  cache:
    clear_delay_sec: 600
files:
  music_cache: music_cache
```

---

## 🧩 Використання

```python
from app.infrastructure.music import MusicSender, MusicRecommendation, MusicFileManager, YtDownloader
from app.config.config_service import ConfigService
from app.domain.ai import ProductPromptDTO

config = ConfigService()
recommender = MusicRecommendation(openai_service, prompt_service, config)
downloader = YtDownloader(config)
file_manager = MusicFileManager(config)
sender = MusicSender(downloader, file_manager, config)

# Отримати рекомендації
dto = ProductPromptDTO(title="YoungLA Hoodie", description="Soft cotton hoodie", image_url="")
result = await recommender.recommend(dto)

# Надіслати в Telegram (update/context — з python-telegram-bot)
await sender.send_recommendations(update, context, result)
```

---

## 👤 Автор
**Кирилл / @key27**
