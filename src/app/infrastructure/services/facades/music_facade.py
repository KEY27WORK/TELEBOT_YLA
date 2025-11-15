# 🎵 app/infrastructure/services/facades/music_facade.py
"""
🎵 `MusicFacade` — тонка обгортка для музичних рекомендацій.

🔹 Ізолює виклик `MusicRecommendation`, щоб оркестратор працював із простим DTO.  
🔹 Конвертує `ProductInfo` у `ProductPromptDTO` і повертає лише перший доречний трек.  
🔹 Повертає `None`, якщо сервіс не дав релевантних рекомендацій (best-effort).
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування фасаду
from dataclasses import dataclass										# 🧱 DTO рекомендації
from types import SimpleNamespace											# 🧰 Простий контейнер для трека
from typing import Optional												# 🧰 Типізація для полів

# 🧩 Внутрішні модулі проєкту
from app.domain.ai import ProductPromptDTO								# 🧠 Промт для музики
from app.domain.products.entities import ProductInfo					# 📦 Дані про товар
from app.infrastructure.music.music_recommendation import MusicRecommendation  # 🎵 Сервіс рекомендацій
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базовий логер

logger = logging.getLogger(LOG_NAME)										# 🧾 Логер фасаду


@dataclass(frozen=True, slots=True)
class MusicSuggest:
    """🎵 DTO для блоків «музика поруч з товаром»."""

    title: str															# 🏷️ Назва треку (artist — title)
    url: Optional[str] = None											# 🔗 URL треку (якщо доступний)


class MusicFacade:
    """
    🎧 Обгортка над `MusicRecommendation`.

    Завдання фасаду:
      • сформувати `ProductPromptDTO` із `ProductInfo`;
      • взяти перший релевантний трек і перетворити його в `MusicSuggest`;
      • не відправляти музику — лише готувати дані для інших шарів.
    """

    def __init__(self, recommendation: MusicRecommendation) -> None:
        self._recommendation = recommendation							# 🎵 Зберігаємо сервіс рекомендацій
        logger.debug("🎵 MusicFacade ініціалізовано.")

    async def maybe_recommend(self, product: ProductInfo) -> Optional[MusicSuggest]:
        """
        🔄 Повертає `MusicSuggest` або `None`, якщо рекомендацій немає.

        Args:
            product (ProductInfo): Дані про товар із парсера.

        Returns:
            MusicSuggest | None: DTO для UI-шару або None (коли немає треків).
        """
        prompt = ProductPromptDTO(										# 🧠 Формуємо промт для AI
            title=getattr(product, "title", "") or "",
            description=getattr(product, "description", "") or "",
            image_url=getattr(product, "image_url", "") or "",
        )
        logger.info("🎵 Запит музичної рекомендації для '%s'", prompt.title[:80])
        result = await self._recommendation.recommend(prompt)			# 🎵 Отримуємо рекомендації
        first_track = self._extract_first_track(result)					# 🎚️ Беремо перший трек
        if not first_track:
            logger.info("🎵 Рекомендації відсутні.")
            return None													# 🚫 Немає сенсу показувати музичний блок

        title = (
            getattr(first_track, "title", None)
            or (first_track.get("title") if isinstance(first_track, dict) else "")
        )																	# 🏷️ Назва з DTO/словаря
        url = (
            getattr(first_track, "url", None)
            or (first_track.get("url") if isinstance(first_track, dict) else None)
        )																	# 🔗 Лінк, якщо доступний
        logger.debug("🎵 Рекомендовано трек: %s (url=%s)", title, url)
        return MusicSuggest(title=title, url=url) if title else None		# 📦 Обгортаємо у DTO або повертаємо None

    # ================================
    # 🧱 ВСПОМОЖНІ МЕТОДИ
    # ================================
    def _extract_first_track(self, recommendation_result: Optional[object]) -> Optional[object]:
        """
        🎶 Дістає перший релевантний трек із результату рекомендацій.

        Args:
            recommendation_result (object | None): Відповідь `MusicRecommendation`.

        Returns:
            object | None: DTO/dict з інформацією про трек, або None.
        """
        if not recommendation_result:
            logger.debug("🎵 Рекомендаційний сервіс повернув None.")
            return None													# 🚫 Нічого не прийшло

        tracks = getattr(recommendation_result, "tracks", None)			# 🎧 Список рекомендацій
        if not tracks:
            logger.debug("🎵 Поле tracks порожнє або відсутнє.")
            return None													# 💤 Список порожній або відсутній

        first = tracks[0] if len(tracks) else None						# 🔢 Беремо перший елемент
        if not first:
            return None

        # 🏷️ Формуємо заголовок у форматі "artist — title", якщо обидва поля є
        artist = getattr(first, "artist", "") or ""
        title_only = getattr(first, "title", "") or ""
        combined_title = f"{artist} — {title_only}" if artist and title_only else (artist or title_only)

        logger.debug("🎵 Перший трек: artist='%s' title='%s'", artist, title_only)
        return SimpleNamespace(											# 📦 Поводимося як із DTO
            title=combined_title,
            url=getattr(first, "url", None),
        )
