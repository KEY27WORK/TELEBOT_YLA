""" 🎵 music_sender.py — клас для надсилання музики в Telegram.

🔹 Відповідає за:
- Парсинг тексту з треками
- Завантаження треків з YouTube (асинхронно)
- Групування треків по розміру
- Надсилання у Telegram: список + медіа-групи
- Очищення кешу після надсилання
"""

# 🌐 Telegram
from telegram import Update, InputMediaAudio
from telegram.ext import CallbackContext
from telegram.constants import ChatAction

# 🧱 Системні
import asyncio
import logging
import os

# 🎵 Музика
from bot.music.music_file_manager import MusicFileManager

logger = logging.getLogger(__name__)


class MusicSender:
    """
    🎵 Відповідає за:
    - Парсинг списку треків
    - Завантаження mp3 з YouTube через MusicFileManager
    - Групування треків за розміром
    - Відправку в Telegram (як список і як групу аудіо)
    - Очищення кешу
    """

    MAX_GROUP_SIZE_MB = 45

    def __init__(self):
        self.cache: list[tuple[str, str]] = []
        self.manager = MusicFileManager()

    def parse_song_list(self, music_text: str) -> list[str]:
        """
        🎶 Парсить текст і повертає список назв треків.
        """
        return self.manager.parse_song_list(music_text)

    def format_track_list(self, track_names: list[str]) -> str:
        """
        📝 Формує текстовий список треків з нумерацією.
        """
        lines = [f"{i + 1}. {name}" for i, name in enumerate(track_names)]
        return "🎵 <b>Музика для поста:</b>\n" + "\n".join(lines)

    async def preload_tracks_async(self, track_names: list[str]):
        """
        🚀 Фонова предзагрузка треків без відправки.
        """
        self.cache = await self.download_all_tracks(track_names)

    async def download_all_tracks(self, track_names: list[str]) -> list[tuple[str, str]]:
        """
        📥 Завантажує всі треки з YouTube асинхронно (одночасно).
        Повертає лише ті треки, які вдалося успішно завантажити.
        """
        tasks = [self.manager.async_find_or_download_track(name) for name in track_names]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[tuple[str, str]] = []
        for name, path in zip(track_names, results_raw):
            if isinstance(path, Exception):
                logging.warning(f"⚠️ Трек пропущено через помилку: {name} — {path}")
                results.append((name, None))
            else:
                results.append((name, path))

        if not any(p for _, p in results):
            logging.error("❌ Не вдалося завантажити жодного треку.")
        else:
            count = sum(1 for _, p in results if p)
            logging.info(f"✅ Успішно завантажено {count} з {len(track_names)} треків.")

        return results

    def group_by_size(self, tracks: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
        """
        📦 Групує треки по ~45MB для надсилання в Telegram.
        """
        groups = []
        current_group = []
        current_size = 0

        for name, path in tracks:
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            if (current_size + file_size_mb > self.MAX_GROUP_SIZE_MB) and current_group:
                groups.append(current_group)
                current_group = []
                current_size = 0

            current_group.append((name, path))
            current_size += file_size_mb

        if current_group:
            groups.append(current_group)

        return groups

    async def send_all_tracks(self, update: Update, context: CallbackContext, track_names: list[str]):
        """
        📤 Повна відправка: список + медіа-групи з треками.
        """
        await update.message.chat.send_action(action="upload_audio")

        try:
            # 1️⃣ Відправляємо список треків
            await update.message.reply_text(self.format_track_list(track_names), parse_mode="HTML")

            # 2️⃣ Якщо preload не спрацював — завантажуємо вручну
            if not self.cache:
                self.cache = await self.download_all_tracks(track_names)

            successful = [(n, p) for n, p in self.cache if p]
            failed = [n for n, p in self.cache if not p]

            if failed:
                failed_list = "\n".join(f"• {name}" for name in failed)
                await update.message.reply_text(
                    f"⚠️ Деякі треки не вдалося завантажити:\n{failed_list}",
                    parse_mode="HTML"
                )

            if not successful:
                await update.message.reply_text("❌ Не вдалося надіслати жодного треку.")
                return

            # 3️⃣ Ділимо на групи та надсилаємо паралельно
            tasks = []
            for group in self.group_by_size(successful):
                media = [
                    InputMediaAudio(media=open(path, "rb"), caption=f"<b>{name}</b>", parse_mode="HTML")
                    for name, path in group
                ]
                tasks.append(update.message.reply_media_group(media))

            await asyncio.gather(*tasks)

            await update.message.reply_text(
                f"✅ Успішно надіслано {len(successful)} треків 🎧",
                parse_mode="HTML"
            )

        except Exception as e:
            logging.error(f"❌ Помилка при відправці треків: {e}")
            await update.message.reply_text("⚠️ Помилка при завантаженні треків")

        asyncio.create_task(asyncio.to_thread(self.clear_cache))


    def clear_cache(self):
        """
        🧹 Очищає кеш mp3-файлів через менеджер.
        """
        self.manager.clear_cache()