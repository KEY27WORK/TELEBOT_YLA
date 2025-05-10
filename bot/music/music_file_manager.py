""" 🎼 music_file_manager.py — менеджер роботи з mp3-треками (завантаження, кешування, парсинг списку).

🔹 Клас:
- `MusicFileManager` — менеджер:
    - кешу для mp3
    - завантаження треків з YouTube
    - парсинг текстових списків треків

Використовує:
- yt_dlp
- FFmpeg (для конвертації в mp3)
- asyncio для паралельного завантаження
- logging для логування
"""

# 📦 Стандартна бібліотека Python
import os
import re
import glob
import time
import logging
import asyncio
from typing import List, Optional

# 🎵 Зовнішні бібліотеки
import yt_dlp
from yt_dlp.utils import DownloadError

# 🛠️ Логер
logger = logging.getLogger(__name__)


class MusicFileManager:
    """
    🎵 Менеджер mp3-файлів: кеш, завантаження, парсинг.
    """

    CACHE_DIR = "music_cache"
    MAX_CONCURRENT_DOWNLOADS = 10
    DOWNLOAD_TIMEOUT = 15

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def clear_cache(self):
        """
        🧹 Безпечне очищення кешу з перевіркою існування файлів.
        Чекає 2 секунди перед видаленням, щоб уникнути конфліктів з yt-dlp.
        """
        time.sleep(2)  # ⏳ Дати ffmpeg і yt-dlp завершити postprocessing

        files = glob.glob(os.path.join(self.CACHE_DIR, "*.mp3"))
        for f in files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    logger.info(f"🧺 Видалено з кешу: {f}")
                except Exception as e:
                    logger.warning(f"⚠️ Не вдалося видалити файл {f}: {e}")


    def get_cached_filename(self, track_name: str) -> str:
        """
        📁 Генерує шлях до mp3-файлу з очищеною назвою.
        """
        clean_name = re.sub(r"[^\w\s\-\(\)\[\]]", "", track_name).strip()
        clean_name = re.sub(r"\s+", "_", clean_name)
        return os.path.join(self.CACHE_DIR, f"{clean_name}.mp3")

    def is_cached(self, track_name: str) -> bool:
        """
        📦 Перевіряє, чи трек вже є в кеші.
        """
        return os.path.exists(self.get_cached_filename(track_name))

    def download_from_youtube(self, track_name: str) -> str:
        """
        📥 Завантажує трек з YouTube і зберігає у вигляді mp3 у кеші.
        """
        final_path = self.get_cached_filename(track_name)
        temp_path = final_path.replace(".mp3", "")

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'outtmpl': temp_path + '.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        query = f"ytsearch1:{track_name}"
        try:
            logger.info(f"⬇️ Завантаження з YouTube: {track_name}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])

            if not os.path.exists(final_path):
                raise FileNotFoundError(f"❌ Трек не збережено як mp3: {track_name}")

            logger.info(f"✅ Успішно завантажено: {track_name}")
            return final_path

        except DownloadError as de:
            logger.error(f"🚫 YouTube помилка для '{track_name}': {de}")
            raise
        except Exception as e:
            logger.error(f"❌ Невідома помилка завантаження '{track_name}': {e}")
            raise

    def find_or_download_track(self, track_name: str) -> str:
        """
        🔁 Повертає шлях до mp3: з кешу або після завантаження.
        """
        if self.is_cached(track_name):
            logger.info(f"🎵 Трек знайдено в кеші: {track_name}")
            return self.get_cached_filename(track_name)

        return self.download_from_youtube(track_name)

    async def async_find_or_download_track(self, name: str) -> str:
        """
        ⚡ Асинхронна обгортка для find_or_download_track, виконується в окремому потоці.
        """
        return await asyncio.to_thread(self.find_or_download_track, name)

    def download_track(self, track_url: str) -> Optional[str]:
        """
        ⬇️ Завантажує один трек через yt_dlp (ytsearch:... або URL). Повертає шлях до mp3.
        """
        try:
            output_template = os.path.join(self.CACHE_DIR, "%(title)s.%(ext)s")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "quiet": True,
                "noplaylist": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(track_url, download=True)
                title = info_dict.get("title", "")
                filename = os.path.join(self.CACHE_DIR, f"{title}.mp3")
                return filename if os.path.exists(filename) else None
        except DownloadError as e:
            logger.warning(f"❌ Помилка завантаження {track_url}: {e}")
            return None

    async def _async_download_track(self, url: str) -> Optional[str]:
        """
        ⚡ Асинхронне завантаження треку з таймаутом і обмеженням паралельності.
        """
        try:
            async with asyncio.Semaphore(self.MAX_CONCURRENT_DOWNLOADS):
                return await asyncio.wait_for(
                    asyncio.to_thread(self.download_track, url),
                    timeout=self.DOWNLOAD_TIMEOUT
                )
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося завантажити {url}: {e}")
            return None

    async def download_multiple_tracks(self, urls: List[str]) -> List[str]:
        """
        🚀 Паралельне завантаження до 10 треків одночасно. Повертає тільки успішні.
        """
        tasks = [self._async_download_track(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]

    @staticmethod
    def parse_song_list(text: str) -> list[str]:
        """
        📜 Парсить список треків із тексту.
        """
        lines = text.strip().split("\n")
        return [line.split(". ", 1)[1].strip() for line in lines if ". " in line]
