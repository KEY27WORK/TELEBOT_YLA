# 📥 src/app/infrastructure/music/yt_downloader.py
"""
📥 YtDownloader — завантажує треки з YouTube через `yt-dlp` та конвертує їх у MP3.

🔹 Працює з доменними DTO `RecommendedTrack` та `TrackInfo`.
🔹 Підтримує кешування MP3 у директорії, що задається конфігом.
🔹 Враховує налаштовувані таймаути, ретраї та цільовий бітрейт.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import asyncio													# 🔁 Відправляємо блокуючі операції в thread-pool
import logging													# 🧾 Логування кроків завантаження
import os														# 📁 Робота з файловою системою
import re														# 🧪 Очищення назв
import time														# ⏱️ Backoff між спробами

import yt_dlp													# 🎬 Бібліотека для завантаження YouTube
from yt_dlp.utils import YoutubeDLError						# 🛑 Спільний базовий виняток

# 🔠 Системні імпорти
from typing import Any, Dict, MutableMapping, cast			# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService				# ⚙️ Конфігураційний сервіс
from app.domain.music.interfaces import (
    IMusicDownloader,
    RecommendedTrack,
    TrackInfo,
)																# 🎵 Доменні контракти
from app.shared.utils.logger import LOG_NAME					# 🏷️ Імʼя логера


logger = logging.getLogger(LOG_NAME)							# 🧾 Ініціалізований логер


# ================================
# 🎧 ЗАВАНТАЖУВАЧ
# ================================
class YtDownloader(IMusicDownloader):
    """
    🎧 Інкапсулює логіку завантаження треків і постобробки в MP3.
    """

    def __init__(self, config: ConfigService) -> None:
        """
        ⚙️ Зчитує конфігурацію та готує директорію кешу.
        """
        self._config = config										# 📦 Зберігаємо джерело налаштувань
        self._cache_dir: str = str(config.get("files.music_cache", "music_cache"))
        os.makedirs(self._cache_dir, exist_ok=True)				# 📁 Гарантуємо наявність директорії

        self._socket_timeout = int(config.get("music.download.socket_timeout", 15) or 15)	# ⏱️ Таймаут сокета
        self._retries = int(config.get("music.download.retries", 3) or 3)	# 🔁 Спроби завантаження
        self._fragment_retries = int(config.get("music.download.fragment_retries", 3) or 3)	# 🔁 Повтори фрагментів
        self._concurrent_fragments = int(config.get("music.download.concurrent_fragments", 4) or 4)	# 📥 Паралельні фрагменти
        self._preferred_bitrate = str(config.get("music.download.mp3_bitrate_kbps", "192") or "192")	# 🎚️ Бітрейт

    # ================================
    # 🔄 ПУБЛІЧНИЙ API
    # ================================
    async def download(self, track: RecommendedTrack) -> TrackInfo:
        """
        🔄 Асинхронна обгортка: виконує блокуюче завантаження в thread-pool.
        """
        return await asyncio.to_thread(self._blocking_download, track)

    # ================================
    # 🧱 ВНУТРІШНЯ ЛОГІКА
    # ================================
    def _blocking_download(self, track: RecommendedTrack) -> TrackInfo:
        """
        🧱 Синхронна частина: викликає `yt-dlp` та postprocessing FFmpeg.
        """
        display_name = self._display_name(track)								# 🏷️ Людинозрозуміла назва
        final_path = self._generate_path(display_name)						# 💾 Фінальний шлях до MP3

        if os.path.exists(final_path):
            logger.info("🎵 Трек уже є в кеші: %s", final_path)
            return TrackInfo(name=display_name, file_path=final_path)

        temp_base = final_path[:-4]											# 📁 Тимчасова основа без `.mp3`
        archive_path = os.path.join(self._cache_dir, "download_archive.txt")	# 🗃️ Файл обліку завантажень

        ydl_opts: Dict[str, object] = {
            "format": "bestaudio/best",					# 🔊 Краща доступна аудіодоріжка
            "noplaylist": True,						# 🚫 Без плейлистів
            "quiet": True,							# 🤫 Менше логів yt-dlp
            "outtmpl": temp_base + ".%(ext)s",			# 🗂️ Шаблон вихідного файлу
            "socket_timeout": self._socket_timeout,		# ⏱️ Таймаут сокета
            "download_archive": archive_path,			# 🗃️ Щоб не качати двічі
            "retries": self._retries,					# 🔁 Спроби завантаження
            "fragment_retries": self._fragment_retries,	# 🔁 Повтори фрагментів
            "concurrent_fragment_downloads": self._concurrent_fragments,	# 📥 Паралельні фрагменти
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self._preferred_bitrate,
                }
            ],
        }

        query = f"ytsearch1:{display_name}"								# 🔍 Запит до yt-dlp (перший результат)

        def _make_opts() -> MutableMapping[str, Any]:
            """
            🧰 Повертає копію опцій для кожного запуску `YoutubeDL`.
            """
            return cast(MutableMapping[str, Any], ydl_opts.copy())

        delay = 1.5														# ⏱️ Початковий backoff
        for attempt in range(1, self._retries + 1):						# 🔁 Кілька спроб завантажити трек
            try:
                logger.info("⬇️ Завантаження (%s/%s): %s", attempt, self._retries, display_name)
                with yt_dlp.YoutubeDL(_make_opts()) as ydl:  # type: ignore[arg-type]
                    ydl.download([query])								# 🎬 Стартуємо yt-dlp

                if not os.path.exists(final_path):						# ⚠️ MP3 ще не створено
                    logger.warning("⚠️ Архів містить запис, але MP3 немає. Повтор без archive…")
                    ydl_opts.pop("download_archive", None)				# 🗃️ Видаляємо archive, щоб не пропустити
                    with yt_dlp.YoutubeDL(_make_opts()) as ydl_retry:  # type: ignore[arg-type]
                        ydl_retry.download([query])					# 🔁 Пробуємо ще раз

                if not os.path.exists(final_path):						# 🚫 Навіть після повтору файлу нема
                    raise FileNotFoundError("Після постпроцесингу MP3 не знайдено.")

                logger.info("✅ Завершено: %s", final_path)				# 🎉 Успішне завантаження
                return TrackInfo(name=display_name, file_path=final_path)

            except (YoutubeDLError, FileNotFoundError) as err:			# ⚠️ Відомі помилки
                logger.warning("⚠️ Спроба %s не вдалася: %s", attempt, err)
                if attempt >= self._retries:
                    break
                time.sleep(delay)										# 😴 Чекаємо перед повтором
                delay *= 1.8											# 📈 Збільшуємо backoff
            except Exception as err:  # noqa: BLE001
                logger.exception("Несподівана помилка завантаження: %s", err)	# 💥 Інші помилки
                break

        return TrackInfo(name=display_name, error="Не вдалося завантажити трек.")

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    @staticmethod
    def _display_name(track: RecommendedTrack) -> str:
        """
        🏷️ Формує уніфіковане імʼя треку для пошуку/файлу.
        """
        display_attr = getattr(track, "display_name", None)	# 🔎 Дивимося, чи вже є display_name
        if isinstance(display_attr, str) and display_attr.strip():	# ✅ Використовуємо готове імʼя
            return display_attr.strip()

        artist = getattr(track, "artist", "") or ""	# 🎙️ Артист із DTO
        title = getattr(track, "title", "") or ""	# 🎵 Назва треку
        combined = f"{artist} – {title}".strip(" –")	# 🧼 Склеюємо й прибираємо зайві тире
        return combined or (title or artist or "track")	# 🆘 Фолбек: беремо будь-яке непорожнє значення

    def _generate_path(self, display_name: str) -> str:
        """
        📁 Генерує шлях до MP3 з очищеною назвою.
        """
        clean = self._clean_name(display_name)	# 🧼 Нормалізуємо імʼя
        return os.path.join(self._cache_dir, f"{clean}.mp3")	# 🛣️ будуємо абсолютний шлях

    @staticmethod
    def _clean_name(name: str) -> str:
        """
        🧼 Очищує імʼя від небезпечних символів і підміняє пробіли на `_`.
        """
        sanitized = re.sub(r"[^\w\s\-\(\)\[\]]", "", name or "").strip()	# 🚫 Заборонені символи
        return re.sub(r"\s+", "_", sanitized)	# ↔️ Заміна пробілів на підкреслення
