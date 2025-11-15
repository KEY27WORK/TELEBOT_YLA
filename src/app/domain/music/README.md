# 🎵 Music Domain

Домен **music**. Містить лише контракти та DTO для роботи з музичною підсистемою.  
Не залежить від інфраструктури (yt-dlp, OpenAI тощо) — тільки від абстракцій.

---

## 📁 Структура

```bash
music/
├──  __init__.py
└── interfaces.py
```
---

## 🧱 Складові

### `interfaces.py`
- **DTO**
  - `RecommendedTrack` — структурований трек (`artist`, `title`).
  - `MusicRecommendationResult` — результат рекомендацій (список треків, сирий текст, модель).
  - `TrackInfo` — інформація про трек (назва, шлях до кешу, помилка).
- **Контракти**
  - `IMusicRecommender` — добірка музики за DTO продукту (`ProductPromptDTO`).
  - `IMusicDownloader` — завантаження структурованого треку (`RecommendedTrack` → `TrackInfo`).
  - `IMusicFileManager` — кешування / очищення треків.

---

## 🚀 Використання

```python
from app.domain.music import IMusicRecommender, RecommendedTrack

async def example(recommender: IMusicRecommender):
    from app.domain.ai import ProductPromptDTO
    product = ProductPromptDTO(title="YoungLA Tee", description="Чорна футболка", image_url=None)
    result = await recommender.recommend(product)
    for track in result.tracks:
        print(f"{track.artist} — {track.title}")
```

## ✅ Гарантії
	•	Чистий домен (ніякої інфри).
	•	DTO — frozen=True, slots=True.
	•	Контракти через Protocol або ABC.
	•	Структуровані дані замість рядків.