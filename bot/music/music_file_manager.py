""" 🎼 music_file_manager.py — менеджер роботи з mp3-треками (завантаження, кешування, парсинг списку).

🔹 Клас:
- `MusicFileManager` — менеджер:
    - кешу для mp3
    - завантаження треків з YouTube
    - парсинг текстових списків треків

Використовує:
- yt_dlp
- FFmpeg (для конвертації в mp3)
- logging
"""

# 🧱 Системні
import os
import re
import glob
import logging

# ⬇️ Завантаження
import yt_dlp
from yt_dlp.utils import DownloadError

class MusicFileManager:
    """
    🎵 Менеджер mp3-файлів: кеш, завантаження, парсинг.
    """

    CACHE_DIR = "music_cache"

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def clear_cache(self):
        """
        🧹 Видаляє всі mp3-файли з кешу.
        """
        files = glob.glob(os.path.join(self.CACHE_DIR, "*.mp3"))
        for f in files:
            try:
                os.remove(f)
                logging.info(f"🧺 Видалено з кешу: {f}")
            except Exception as e:
                logging.warning(f"⚠️ Не вдалося видалити файл {f}: {e}")

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
            logging.info(f"⬇️ Завантаження з YouTube: {track_name}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])

            if not os.path.exists(final_path):
                raise FileNotFoundError(f"❌ Трек не збережено як mp3: {track_name}")

            logging.info(f"✅ Успішно завантажено: {track_name}")
            return final_path

        except DownloadError as de:
            logging.error(f"🚫 YouTube помилка для '{track_name}': {de}")
            raise
        except Exception as e:
            logging.error(f"❌ Невідома помилка завантаження '{track_name}': {e}")
            raise

    def find_or_download_track(self, track_name: str) -> str:
        """
        🔁 Повертає шлях до mp3: з кешу або після завантаження.
        """
        if self.is_cached(track_name):
            logging.info(f"🎵 Трек знайдено в кеші: {track_name}")
            return self.get_cached_filename(track_name)

        return self.download_from_youtube(track_name)

    @staticmethod
    def parse_song_list(text: str) -> list[str]:
        """
        📜 Парсить список треків із тексту.
        """
        lines = text.strip().split("\n")
        return [line.split(". ", 1)[1].strip() for line in lines if ". " in line]
