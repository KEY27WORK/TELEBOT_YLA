# 🎵 app/domain/music/interfaces.py
"""
🎵 Модуль описує DTO й контракти домену музичних рекомендацій.

🔹 Містить суворо типізовані структури RecommendedTrack/MusicRecommendationResult/TrackInfo.
🔹 Визначає протоколи IMusicRecommender/IMusicDownloader/IMusicFileManager для слабкого зв'язування.
🔹 Не містить інфраструктури — лише чистий домен, синхронізований із ProductPromptDTO (AI).
"""

from __future__ import annotations                                                   # ⏳ Дозволяємо посилатися на типи нижче

# 🔠 Системні імпорти
import logging                                                                       # 🧾 Єдиний канал логування
from dataclasses import dataclass                                                    # 🧱 Структуруємо DTO
from typing import Optional, Protocol, Sequence, runtime_checkable                   # 🧰 Типи, послідовності та Protocol

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME                                         # 🏷️ Базове ім'я логера застосунку
from app.domain.ai import ProductPromptDTO                                          # 🤖 DTO промпта продукту


# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
MODULE_LOGGER_NAME: str = f"{LOG_NAME}.domain.music.interfaces"                      # 🏷️ Спеціальний префікс логера
logger = logging.getLogger(MODULE_LOGGER_NAME)                                       # 🧾 Отримуємо логер для модуля
logger.debug("🎵 Імпортовано music.interfaces | logger=%s", MODULE_LOGGER_NAME)      # 🚀 Фіксуємо ініціалізацію


# ================================
# 🏛️ DTO (Data Transfer Objects)
# ================================
@dataclass(frozen=True, slots=True)
class RecommendedTrack:
    """
    ✅ Структурований опис одного рекомендованого треку.
    """

    artist: str                                                                       # 🧑‍🎤 Виконавець треку
    title: str                                                                        # 🎼 Назва треку

    def __post_init__(self) -> None:
        """
        Логує створення треку та перевіряє базові інваріанти (непорожні поля).
        """
        logger.debug("🎧 RecommendedTrack створено | artist=%r title=%r", self.artist, self.title)  # 🧾 Фіксуємо DTO
        if not self.artist.strip():                                                   # 🚫 Перевіряємо виконавця
            logger.warning("⚠️ RecommendedTrack без artist | title=%r", self.title)   # ⚠️ Попереджаємо про порожній artist
        if not self.title.strip():                                                    # 🚫 Перевіряємо назву
            logger.warning("⚠️ RecommendedTrack без title | artist=%r", self.artist)  # ⚠️ Попереджаємо про порожній title

    @property
    def display_name(self) -> str:
        """Зручне представлення «Виконавець — Назва» для UI/логів."""
        display_value: str = f"{self.artist} — {self.title}"                          # 🪪 Готуємо людинозрозумілий підпис
        logger.debug("🪪 RecommendedTrack.display_name викликано | value=%r", display_value)  # 🧾 Діагностуємо побудову
        return display_value                                                          # 📤 Повертаємо підготовлений рядок


@dataclass(frozen=True, slots=True)
class MusicRecommendationResult:
    """
    📦 Результат роботи сервісу музичних рекомендацій.
    """

    tracks: Sequence[RecommendedTrack]                                                # 🎯 Список структурованих треків
    raw_text: str                                                                     # 🧾 Сирий текст моделі (для трасування)
    model: str                                                                        # 🤖 Ідентифікатор моделі (наприклад, gpt-4o)

    def __post_init__(self) -> None:
        """
        Логує формування рекомендацій та їх ключові параметри.
        """
        tracks_count: int = len(self.tracks)                                          # 🔢 Кількість треків у добірці
        logger.debug(
            "📦 MusicRecommendationResult сформовано | tracks=%d model=%r raw_len=%d",
            tracks_count,
            self.model,
            len(self.raw_text),
        )                                                                             # 🧾 Фіксуємо мета-інформацію
        if tracks_count == 0:                                                         # 🚫 Відсутні рекомендації
            logger.info("ℹ️ MusicRecommendationResult без треків | model=%r", self.model)  # ℹ️ Інформуємо для дебагу


@dataclass(frozen=True, slots=True)
class TrackInfo:
    """
    🎼 Результат завантаження/пошуку конкретного треку.
    """

    name: str                                                                         # 🏷️ Людяна назва треку
    file_path: Optional[str] = None                                                   # 🗂️ Повний шлях до локального файлу
    error: Optional[str] = None                                                       # ❌ Опис проблеми (якщо сталася)

    def __post_init__(self) -> None:
        """
        Логує результат завантаження з урахуванням успіху/помилки.
        """
        logger.debug(
            "🎼 TrackInfo створено | name=%r has_file=%s has_error=%s",
            self.name,
            bool(self.file_path),
            bool(self.error),
        )                                                                             # 🧾 Фіксуємо стан DTO
        if self.error:                                                                # 🚫 Є помилка під час завантаження
            logger.warning("⚠️ TrackInfo error | name=%r error=%r", self.name, self.error)  # ⚠️ Попереджаємо


# ================================
# 🧩 ІНТЕРФЕЙСИ (КОНТРАКТИ)
# ================================
@runtime_checkable
class IMusicRecommender(Protocol):
    """
    🔎 Контракт сервісу підбору музики за даними про продукт/картинку.
    Працює на рівні доменних DTO, не знає про конкретні LLM/SaaS.
    """

    async def recommend(self, product: ProductPromptDTO) -> MusicRecommendationResult:
        """
        Згенерувати добірку треків на основі вхідних метаданих продукту.

        Args:
            product: ProductPromptDTO з title/description/image_url.

        Returns:
            MusicRecommendationResult: структуровані треки + сирий вихід моделі.
        """
        ...


logger.debug("🎯 IMusicRecommender protocol задекларовано")                           # 🧾 Контракт доступний


@runtime_checkable
class IMusicDownloader(Protocol):
    """
    ⬇️ Контракт сервісу завантаження треків (пошук і збереження локально).
    """

    async def download(self, track: RecommendedTrack) -> TrackInfo:
        """
        Завантажити трек на основі структурованих метаданих.

        Args:
            track: RecommendedTrack {artist, title}.

        Returns:
            TrackInfo: шлях до файлу або опис помилки.
        """
        ...


logger.debug("⬇️ IMusicDownloader protocol задекларовано")                            # 🧾 Контракт завантаження готовий


@runtime_checkable
class IMusicFileManager(Protocol):
    """
    🗃️ Контракт менеджера файлового кешу музики.
    """

    def get_cached_path(self, track: RecommendedTrack) -> Optional[str]:
        """
        Перевірити, чи є вже завантажений трек у кеші.

        Args:
            track: RecommendedTrack.

        Returns:
            Повний шлях до файлу або None, якщо відсутній.
        """
        ...

    async def clear_cache(self) -> None:
        """Асинхронне очищення кешу музичних файлів."""
        ...


logger.debug("🗃️ IMusicFileManager protocol задекларовано")                          # 🧾 Контракт файлового кешу готовий


# ================================
# 📦 ПУБЛІЧНИЙ API МОДУЛЯ
# ================================
__all__ = [
    # DTO
    "RecommendedTrack",                                                               # 🎧 DTO одного треку
    "MusicRecommendationResult",                                                      # 📦 Результат рекомендацій
    "TrackInfo",                                                                      # 🎼 DTO результату завантаження
    # Interfaces
    "IMusicRecommender",                                                              # 🔎 Контракт рекомендацій
    "IMusicDownloader",                                                               # ⬇️ Контракт завантаження
    "IMusicFileManager",                                                              # 🗃️ Контракт файлового менеджера
]
logger.debug("🔓 __all__ оголошено: %s", __all__)                                     # 🧾 Фіксуємо експортовані символи
