# 🎵 app/infrastructure/music/music_recommendation.py
"""
🎵 MusicRecommendation — добір музики до товарів через AI (IMusicRecommender).

🔹 Головний метод `recommend(ProductPromptDTO)` будує prompt і звертається до LLM.
🔹 Фолбек `recommend_legacy` підтримує старе API з title/description/image_url.
🔹 Модель/temperature встановлюються безпосередньо в ChatPrompt, як очікує OpenAIService.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging	# 🧾 Логування кроків рекомендацій
import re	# 🧹 Нормалізація рядків із треками
from typing import List, Tuple	# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService
from app.domain.ai import ProductPromptDTO
from app.domain.music.interfaces import (
    IMusicRecommender,
    MusicRecommendationResult,
    RecommendedTrack,
)
from app.infrastructure.ai.open_ai_serv import OpenAIService
from app.infrastructure.ai.prompt_service import PromptService  # у stubs може не бути методів
from app.shared.utils.logger import LOG_NAME

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)	# 🧾 Використовуємо загальний логер


class MusicRecommendation(IMusicRecommender):
    """🎶 Підбирає музику через LLM: формує prompt, викликає OpenAI, парсить відповіді."""

    def __init__(
        self,
        openai_service: OpenAIService,
        prompt_service: PromptService,
        config_service: ConfigService,
    ) -> None:
        """⚙️ Зберігає залежності та логгує готовність."""
        self._openai = openai_service	# 🤖 API клієнт OpenAI
        self._prompts = prompt_service	# 🧾 Сервіс промтів
        self._config = config_service	# ⚙️ Конфіг (модель/temperature)
        logger.info("✅ MusicRecommendation ініціалізовано.")	# 🪵 Подія

    # ===== Доменно правильний метод (вимога IMusicRecommender) =====
    async def recommend(self, product: ProductPromptDTO) -> MusicRecommendationResult:
        """Згенерувати добірку для продукту (title/description/image_url всередині DTO)."""
        title = product.title or ""
        logger.info("🎼 Підбір музики для: %s", title)

        # Налаштування моделі (строго приводимо типи, щоб не отримати Optional)
        model: str = self._config.get("music.recommendation.model", "gpt-4o-mini") or "gpt-4o-mini"
        temperature: float = self._config.get(  # type: ignore[assignment]
            "music.recommendation.temperature",
            0.7,
            cast=float,
        ) or 0.7

        # Формуємо ChatPrompt для LLM
        prompt = self._prompts.get_music_prompt(product)

        # Кладемо модель/температуру прямо у prompt (так очікує OpenAIService.chat_completion)
        try:
            setattr(prompt, "model", model)
            setattr(prompt, "temperature", float(temperature))
        except Exception:
            logger.debug("ℹ️ Не вдалося виставити model/temperature у ChatPrompt; продовжую.", exc_info=False)

        # Запит до LLM
        raw = await self._openai.chat_completion(prompt)
        if not raw:
            logger.warning("⚠️ AI не повернув відповідь для музичних рекомендацій.")
            return MusicRecommendationResult(tracks=(), raw_text="", model=model)

        tracks = self._parse_response_to_tracks(raw)
        return MusicRecommendationResult(tracks=tuple(tracks), raw_text=raw, model=model)

    # ===== Легаси-обгортка для старих викликів (не входить у контракт) =====
    async def recommend_legacy(self, title: str, description: str, image_url: str) -> MusicRecommendationResult:
        """Сумісність зі старим API. Створює DTO та делегує у recommend()."""
        dto = ProductPromptDTO(title=title or "", description=description or "", image_url=image_url or "")
        return await self.recommend(dto)

    # =========================
    # Helpers (парсинг відповіді)
    # =========================
    def _parse_response_to_tracks(self, text: str) -> List[RecommendedTrack]:
        """
        Видобуває список `RecommendedTrack` з «сирого» тексту моделі.
        Забирає маркери списку і пробує поділити на «Артист — Трек».
        """
        lines = (text or "").splitlines()	# 📄 Розбиваємо текст моделі на рядки
        cleaned: List[str] = []	# 🧼 Зберігаємо очищені рядки
        for line in lines:	# 🔁 Нормалізуємо кожен рядок
            stripped = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s*", "", line).strip()	# ✂️ Прибираємо маркери списку
            if stripped:	# ✅ Ігноруємо порожні рядки
                cleaned.append(stripped)	# 🧺 Додаємо у список

        result: List[RecommendedTrack] = []	# 🎵 Підсумковий список треків
        seen: set[Tuple[str, str]] = set()	# ♻️ Відстежуємо дублікати (artist/title)

        for entry in cleaned:	# 🔁 Обходимо очищені рядки
            artist, title = self._split_artist_title(entry)	# 🎙️ Розбиваємо на артиста/трек
            dedupe_key = (artist.lower(), title.lower())	# 🔑 Кей для унікальності
            if dedupe_key in seen:	# 🚫 Вже доданий
                continue
            seen.add(dedupe_key)	# ♻️ Позначаємо як бачене
            result.append(RecommendedTrack(artist=artist, title=title))	# 📦 Додаємо у результат

        logger.debug("🎶 Parsed %d унікальних треків із відповіді AI.", len(result))	# 🪵 Метрика
        return result	# 🔁 Повертаємо список

    @staticmethod
    def _split_artist_title(s: str) -> Tuple[str, str]:
        """
        Пробуємо «Артист — Трек» з різними тире/дефісами.
        Якщо розділити не вдалося — вся строка вважається назвою треку.
        """
        for separator in (" — ", " – ", " - ", " —", " –", " -"):	# 🔁 Випробовуємо різні тире/дефіси
            if separator in s:	# ✅ Є роздільник
                artist, title = s.split(separator, 1)	# ✂️ Ділимо рядок
                artist, title = artist.strip(), title.strip()	# 🧼 Прибираємо пробіли
                if artist and title:	# ✅ Обидві частини непорожні
                    return artist, title	# 🔁 Повертаємо як (artist, title)
        return "", s.strip()	# 🔁 Default: без артиста, весь рядок — назва треку
