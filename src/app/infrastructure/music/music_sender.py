# 🎵 app/infrastructure/music/music_sender.py
"""
🎵 MusicSender — оркестратор відправлення треків у Telegram.

🔹 Приймає доменні DTO (`RecommendedTrack`, `MusicRecommendationResult`).
🔹 Спочатку відправляє список названь, потім асинхронно — самі mp3.
🔹 Має легасі-шлях для масиву рядків.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio	# ⏱️ Асинхронні семафори/фонова робота
import logging	# 🧾 Логування
from typing import Dict, Iterable, Sequence	# 🧰 Типізація

# 🌐 Зовнішні бібліотеки
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import RetryAfter

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext
from app.config.config_service import ConfigService
from app.domain.music.interfaces import IMusicDownloader, MusicRecommendationResult, RecommendedTrack
from app.shared.utils.logger import LOG_NAME
from .music_file_manager import MusicFileManager

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)	# 🧾 Використовуємо базовий логер застосунку


class MusicSender:
    """🎵 UX: швидкий список треків, далі — аудіо у фоні."""

    def __init__(self, downloader: IMusicDownloader, file_manager: MusicFileManager, config: ConfigService) -> None:
        """⚙️ Зберігає залежності та створює семафори для обмеження паралельності."""
        self._downloader = downloader	# ⬇️ Сервіс завантаження треків
        self._file_manager = file_manager	# 💾 Кеш mp3
        self._config = config	# ⚙️ Джерело параметрів

        dl_limit = int(config.get("music.download.concurrent_downloads", 3) or 3)	# 🔢 Ліміт завантажень
        send_limit = int(config.get("music.send.concurrent_sends", 3) or 3)	# 📤 Ліміт відправлень
        self._dl_semaphore = asyncio.Semaphore(dl_limit)	# 🛡️ Обмеження на скачування
        self._send_semaphore = asyncio.Semaphore(send_limit)	# 🛡️ Обмеження на викладку
        logger.debug("🎵 MusicSender семафори створено (dl=%s send=%s).", dl_limit, send_limit)

        self._inflight: Dict[str, asyncio.Future] = {}	# 🔁 Захист від подвійної обробки

    # ================================
    # 📣 ПУБЛІЧНИЙ API
    # ================================
    async def send_recommendations(self, update: Update, context: CustomContext, result: MusicRecommendationResult) -> None:
        """
        📬 Сучасний шлях: приймає `MusicRecommendationResult` і відправляє список + аудіо.
        """
        if not update.message or not result.tracks:	# 🚫 Немає куди/чого відправляти
            return

        track_names = [track.display_name for track in result.tracks]	# 🧾 Імена для списку
        await update.message.reply_text(self._format_track_list(track_names), parse_mode="HTML")	# 📄 Список треків

        try:
            await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)	# ⌛ Показуємо статус
        except Exception:
            logger.debug("ℹ️ Не вдалося показати ChatAction (UPLOAD_DOCUMENT).", exc_info=False)

        for track in result.tracks:	# 🎧 Стартуємо обробку кожного треку у фоні
            asyncio.create_task(self._process_track_in_background(update, track))

        clear_delay = int(self._config.get("music.cache.clear_delay_sec", 600) or 600)	# 🕒 Затримка очищення
        asyncio.create_task(self._delayed_cache_clear(clear_delay))	# 🧹 Відкладене очищення кешу

    async def send_recommendations_legacy(self, update: Update, context: CustomContext, track_names: Sequence[str]) -> None:
        """♻️ Легасі: приймає список рядків, конвертує у DTO й делегує сучасному методу."""
        tracks = [self._str_to_track(name) for name in track_names if (name or "").strip()]	# 🧾 Фільтруємо/нормалізуємо
        result = MusicRecommendationResult(tracks=tuple(tracks), raw_text="", model="")	# 📦 Обгортка
        await self.send_recommendations(update, context, result)	# 🔁 Делегуємо

    # ================================
    # ⚙️ ВНУТРІШНЄ
    # ================================
    async def _process_track_in_background(self, update: Update, track: RecommendedTrack) -> None:
        """🎧 Завантажує та надсилає один трек у фоні, з урахуванням семафорів/in-flight."""
        if not update.message:	# 🚫 Немає повідомлення
            return

        key = track.display_name	# 🏷️ Унікальний ідентифікатор треку
        inflight_future = self._inflight.get(key)	# 🔁 Чи вже обробляємо цей трек?
        if inflight_future:	# ♻️ Якщо так — просто чекаємо завершення
            await inflight_future
            return

        future = asyncio.get_running_loop().create_future()	# 🪧 Створюємо future
        self._inflight[key] = future	# 🧾 Фіксуємо активне завантаження

        try:
            async with self._dl_semaphore:	# ⛔ Ліміт одночасних завантажень
                track_info = await self._downloader.download(track)	# ⬇️ Завантажуємо mp3

            if track_info.file_path:	# ✅ Завантаження успішне
                async with self._send_semaphore:	# ⛔ Ліміт одночасних відправлень
                    try:
                        with open(track_info.file_path, "rb") as audio_file:	# 📂 Відкриваємо файл
                            await update.message.reply_audio(
                                audio=audio_file,
                                caption=f"🎧 {track_info.name}",
                                parse_mode="HTML",
                                disable_notification=True,
                            )	# 📤 Відправляємо аудіо
                    except FileNotFoundError:	# ⚠️ Файл зник
                        logger.warning("⚠️ Файл зник до моменту відправки: %s", track_info.file_path)
            else:
                logger.warning("⚠️ Трек «%s» не надіслано: %s", key, track_info.error)	# ⚠️ Помилка завантаження

        except RetryAfter as exc:	# ⏳ Ліміт Telegram
            logger.warning("⏳ Вичерпано ліміт відправки. Чекаємо %s сек.", exc.retry_after)
            await asyncio.sleep(exc.retry_after)
            await self._process_track_in_background(update, track)	# 🔁 Повторюємо
        except Exception as exc:  # noqa: BLE001
            logger.exception("💥 Критична помилка під час обробки треку «%s»: %s", key, exc)
        finally:
            future.set_result(True)	# ✅ Завершуємо future
            self._inflight.pop(key, None)	# ♻️ Прибираємо з реєстру

    async def _delayed_cache_clear(self, delay_seconds: int) -> None:
        """🧹 Чекає delay_seconds і запускає очищення кешу."""
        await asyncio.sleep(max(0, int(delay_seconds)))	# ⏱️ Затримка
        logger.info("🧹 Очищення кешу музики після затримки %s сек.", delay_seconds)
        await self._file_manager.clear_cache()	# 🧼 Видаляємо mp3

    @staticmethod
    def _format_track_list(track_names: Iterable[str]) -> str:
        """📝 Формує HTML-список треків для повідомлення."""
        lines = [f"{index + 1}. {name}" for index, name in enumerate(track_names)]	# 🔢 Нумерований список
        return "🎵 <b>Музика для посту:</b>\n" + "\n".join(lines)	# 📄 Форматований текст

    # ================================
    # 🧰 УТИЛІТИ
    # ================================
    @staticmethod
    def _str_to_track(s: str) -> RecommendedTrack:
        """
        🔁 Перетворює рядок «Artist — Title» у DTO. Якщо розділити не вдалося — лише title.
        """
        normalized = (s or "").strip()	# 🧼 Нормалізуємо рядок
        for separator in (" — ", " – ", " - ", "—", "–", "-"):	# 🔁 Перебираємо варіанти тире
            if separator in normalized:
                artist, title = (part.strip() for part in normalized.split(separator, 1))	# ✂️ Ділимо
                if artist and title:	# ✅ Маємо обидві частини
                    return RecommendedTrack(artist=artist, title=title)
        return RecommendedTrack(artist="", title=normalized)	# 🎧 Лише назва треку
