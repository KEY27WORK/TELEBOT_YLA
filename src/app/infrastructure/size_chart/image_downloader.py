# 📥 app/infrastructure/size_chart/image_downloader.py
"""
📥 Безпечне асинхронне завантаження зображень для пайплайна таблиць розмірів.

🔹 Стримить відповіді через `httpx`, контролюючи таймаути й редіректи.
🔹 Перевіряє `Content-Type`, сигнатури PNG/JPEG/GIF/WebP та обмежує розмір.
🔹 Підтримує ретраї з експоненційним backoff і метрики Prometheus.
🔹 Повертає або шлях до збереженого файлу (`download`), або байти з SHA256 (`fetch`).
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio															# ⏳ Контроль затримок між ретраями
import hashlib															# 🔐 Обчислення SHA256
import logging															# 🧾 Логування результатів
import os																# 📁 Робота з файловою системою
import tempfile														# 🧪 Тимчасові файли для атомарного запису
from dataclasses import dataclass										# 🧱 DTO для результатів
from enum import Enum													# 🏷️ Типізація помилок
from pathlib import Path												# 🛤️ Шляхи до файлів
from typing import Awaitable, Callable, Iterable, Optional, Tuple, Union, cast	# 🧰 Допоміжні типи

# 🌐 Зовнішні бібліотеки
import httpx															# 🌐 HTTP-клієнт

try:																	# 📈 Опційні метрики Prometheus
    from prometheus_client import Counter								# type: ignore
except Exception:														# pragma: no cover
    Counter = None														# type: ignore

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME							# 🏷️ Ім'я базового логера

logger = logging.getLogger(f"{LOG_NAME}.downloader")					# 🧾 Локальний логер модуля


# ================================
# 📊 МЕТРИКИ PROMETHEUS
# ================================
if Counter:															# ✅ Ініціалізуємо лічильники, якщо доступні
    DOWNLOAD_ERRORS_TOTAL = Counter(									# 📉 Кількість помилок
        "download_errors_total",
        "Помилки завантаження зображень за причинами",
        ["reason"],
    )
    DOWNLOAD_OK_TOTAL = Counter(										# 📈 Кількість успішних завантажень
        "download_ok_total",
        "Успішні завантаження зображень",
    )
else:
    DOWNLOAD_ERRORS_TOTAL = None										# type: ignore
    DOWNLOAD_OK_TOTAL = None											# type: ignore


def _inc_error(reason: str) -> None:
    """🔢 Інкрементуємо метрику помилок (ігноруємо збої метрик)."""
    if not DOWNLOAD_ERRORS_TOTAL:										# 🚫 Немає метрик — виходимо
        return
    try:
        DOWNLOAD_ERRORS_TOTAL.labels(reason=reason).inc()				# ➕ Додаємо одиницю
    except Exception:
        pass															# 🤫 Не дозволяємо метрикам зламати пайплайн


def _inc_ok() -> None:
    """🔢 Інкрементуємо метрику успішних завантажень."""
    if not DOWNLOAD_OK_TOTAL:											# 🚫 Без метрик — ігноруємо
        return
    try:
        DOWNLOAD_OK_TOTAL.inc()										# ➕ Фіксуємо успішне завантаження
    except Exception:
        pass															# 🤫 Не перериваємо виконання


# ================================
# 📦 КОНСТАНТИ
# ================================
DEFAULT_HEADERS = {													# 📨 Базові HTTP-заголовки
    "User-Agent": "Mozilla/5.0 (compatible; SizeChartBot/1.0; +https://example.org/bot)",
    # ⚠️ Не запитуємо AVIF — Shopify тоді замінює JPEG/PNG і Pillow/OCR його не читають
    "Accept": "image/png,image/jpeg,image/webp,image/apng,*/*;q=0.5",
}
DEFAULT_CT_PREFIXES: Tuple[str, ...] = ("image/",)						# 🏷️ Дозволені префікси Content-Type
MAGIC_SIGNATURES: Tuple[Tuple[bytes, str], ...] = (					# 🧪 Сигнатури файлів
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xFF\xD8", "JPEG"),
    (b"GIF8", "GIF"),
    (b"RIFF", "RIFF"),												# 📌 WebP перевіряємо окремо
)


# ================================
# 📚 DTO РЕЗУЛЬТАТІВ
# ================================
@dataclass(frozen=True)
class DownloadResult:
    """📚 Відомості про збережений файл."""

    path: Path															# 📁 Фінальний шлях
    content_type: Optional[str]										# 🏷️ Визначений тип контенту
    content_length: Optional[int]										# 📏 Розмір згідно заголовку
    bytes_written: int													# 🔢 Фактично записані байти
    sha256: Optional[str]												# 🔐 Хеш файлу (за потреби)


@dataclass(frozen=True, slots=True)
class ImageData:
    """📚 Дані для OCR: байти з SHA256 та метаданими."""

    url: str															# 🌐 Джерельний URL
    content: bytes														# 💾 Скачані байти
    sha256: str															# 🔐 Хеш вмісту
    content_type: Optional[str]										# 🏷️ Content-Type (якщо відомий)


class DownloadError(Enum):
    """🚫 Причини невдалого завантаження."""

    HTTP_STATUS = "http_status"										# 🌐 Некоректний HTTP-статус
    TOO_LARGE = "too_large"											# 📏 Перевищено ліміт розміру
    NOT_IMAGE = "not_image"											# 🏷️ Content-Type не належить до зображень
    MAGIC_MISMATCH = "magic_mismatch"									# 🧪 Сигнатура не схожа на зображення
    IO_ERROR = "io_error"												# 💽 Помилка файлових операцій
    EMPTY_BODY = "empty_body"											# 🕳️ Тіло відповіді порожнє
    UNKNOWN = "unknown"												# ❓ Невідома помилка


DownloadOutcome = Union[DownloadResult, DownloadError]					# 🔀 Результат запису на диск
FetchOutcome = Union[ImageData, DownloadError]							# 🔀 Результат завантаження в пам'ять
RetryOutcome = Union[DownloadError, ImageData, DownloadResult]			# 🎯 Узагальнений результат ретраїв


# ================================
# 📥 ОСНОВНИЙ ЗАВАНТАЖУВАЧ
# ================================
class ImageDownloader:
    """📥 Асинхронно завантажує зображення з перевірками безпеки."""

    def __init__(
        self,
        *,
        timeout_s: float = 30.0,
        headers: Optional[dict] = None,
        ct_prefixes: Iterable[str] = DEFAULT_CT_PREFIXES,
        max_bytes: int = 20 * 1024 * 1024,
        max_attempts: int = 3,
        backoff_base_s: float = 1.0,
        verify_magic: bool = True,
        compute_sha256: bool = False,
        chunk_size: int = 64 * 1024,
    ) -> None:
        self.timeout_s = float(timeout_s)								# ⏳ Таймаут запиту в секундах
        merged_headers = headers or {}
        self.headers = {**DEFAULT_HEADERS, **merged_headers}			# 📨 Підсумкові HTTP-заголовки
        self.ct_prefixes = tuple(ct_prefixes)							# 🏷️ Допустимі префікси типу контенту
        self.max_bytes = int(max_bytes)									# 📏 Максимальний розмір файлу
        self.max_attempts = max(1, int(max_attempts))					# 🔁 Кількість ретраїв
        self.backoff_base_s = float(backoff_base_s)						# 🐢 Базова затримка між ретраями
        self.verify_magic = bool(verify_magic)							# 🧪 Чи перевіряти сигнатуру
        self.compute_sha256 = bool(compute_sha256)						# 🔐 Чи рахувати хеш під час `download`
        self.chunk_size = int(chunk_size)								# 📦 Розмір шматків при стримінгу
        logger.debug(
            "⚙️ ImageDownloader init timeout=%.1fs attempts=%d max_bytes=%d chunk=%d verify_magic=%s compute_sha=%s",
            self.timeout_s,
            self.max_attempts,
            self.max_bytes,
            self.chunk_size,
            self.verify_magic,
            self.compute_sha256,
        )

    # ================================
    # 🔄 ПУБЛІЧНИЙ API
    # ================================
    async def fetch(self, img_url: str) -> ImageData:
        """📦 Завантажує байти в пам'ять; у разі помилки підіймає `RuntimeError`."""
        logger.info("📥 fetch start: %s", img_url)
        outcome = await self._fetch_outcome(img_url)					# 🔄 Повертає DTO або помилку
        if isinstance(outcome, DownloadError):
            logger.error("❌ fetch failed: %s (%s)", img_url, outcome.value)
            raise RuntimeError(f"Image fetch failed: {outcome.value}")	# 🚨 Спрощений API для викликачів
        logger.info(
            "✅ fetch ok: %s (bytes=%d, ct=%s)",
            img_url,
            len(outcome.content),
            outcome.content_type or "n/a",
        )
        return outcome

    async def download(self, img_url: str, output_path: Path) -> DownloadOutcome:
        """💾 Сумісний метод, що повертає `DownloadResult` або помилку."""
        logger.info("💾 download start: %s -> %s", img_url, output_path)
        return await self.download_info(img_url, output_path)			# 🔁 Делегуємо на розширену версію

    async def download_info(self, img_url: str, output_path: Path) -> DownloadOutcome:
        """🔁 Записує файл на диск з ретраями та повертає результат або помилку."""
        outcome = await self._run_with_retries(							# 🔁 Уніфікований механізм ретраїв
            img_url=img_url,
            handler=self._stream_to_disk,
            output_path=Path(output_path),
        )
        if isinstance(outcome, DownloadError):
            logger.error("❌ download_info failed: %s (%s)", img_url, outcome.value)
            return outcome												# 🚫 Помилка завантаження
        logger.info(
            "💾 download_info ok: %s -> %s (bytes=%d)",
            img_url,
            outcome.path,
            outcome.bytes_written,
        )
        return cast(DownloadResult, outcome)							# 💾 Успішно збережений файл

    # ================================
    # 🔁 МЕХАНІКА РЕТРАЇВ
    # ================================
    async def _fetch_outcome(self, img_url: str) -> FetchOutcome:
        """🔄 Внутрішня версія `fetch` з типізованим результатом."""
        logger.debug("📥 _fetch_outcome for %s", img_url)
        outcome = await self._run_with_retries(
            img_url=img_url,
            handler=self._stream_to_memory,
        )
        if isinstance(outcome, DownloadError):
            return outcome												# 🚫 Помилка під час завантаження
        return cast(ImageData, outcome)									# 📦 Повертаємо байти та SHA

    async def _run_with_retries(
        self,
        *,
        img_url: str,
        handler: Callable[..., Awaitable[RetryOutcome]],
        output_path: Optional[Path] = None,
    ) -> RetryOutcome:
        """🔁 Загальний ретрай-рушій для `fetch` та `download`."""
        if not img_url:
            logger.error("❌ URL зображення не передано", extra={"download_error": DownloadError.UNKNOWN.value})
            _inc_error(DownloadError.UNKNOWN.value)
            return DownloadError.UNKNOWN

        logger.debug(
            "🔁 Початок ретраїв для %s (max_attempts=%d, handler=%s).",
            img_url,
            self.max_attempts,
            getattr(handler, "__name__", handler),
        )
        for attempt in range(1, self.max_attempts + 1):
            try:
                timeout = httpx.Timeout(self.timeout_s)					# ⏳ Формуємо таймаут
                async with httpx.AsyncClient(							# 🌐 Створюємо HTTP-клієнт
                    headers=self.headers,
                    timeout=timeout,
                    follow_redirects=True,
                ) as client:
                    async with client.stream("GET", img_url) as response:
                        status_error = self._ensure_status(response, img_url, attempt)
                        if status_error:
                            return status_error						# 🚫 HTTP-статус не пройшов перевірку

                        content_type = self._normalize_ct(response.headers.get("Content-Type"))
                        content_length = self._parse_length(response.headers.get("Content-Length"))

                        ct_error = self._validate_content_type(content_type, img_url)
                        if ct_error:
                            return ct_error							# 🚫 Тип контенту не влаштовує

                        size_error = self._validate_length(content_length, img_url)
                        if size_error:
                            return size_error							# 🚫 Завеликий файл за Content-Length

                        logger.debug(
                            "📡 Отримано відповідь %s (ct=%s, length=%s) attempt %d/%d.",
                            img_url,
                            content_type or "n/a",
                            content_length if content_length is not None else "n/a",
                            attempt,
                            self.max_attempts,
                        )
                        if output_path:
                            result = await handler(						# 💾 Пишемо на диск
                                response,
                                img_url=img_url,
                                output_path=output_path,
                                content_type=content_type,
                                content_length=content_length,
                            )
                            logger.debug("💾 Handler завершився для %s (attempt %d).", img_url, attempt)
                            return result

                        result = await handler(							# 📦 Повертаємо байти
                            response,
                            img_url=img_url,
                            content_type=content_type,
                        )
                        logger.debug("📦 Handler повернув байти для %s (attempt %d).", img_url, attempt)
                        return result

            except httpx.HTTPError as exc:
                code = getattr(getattr(exc, "response", None), "status_code", None)	# 🧾 Код статусу, якщо є
                logger.warning(
                    "⚠️ HTTP-помилка (%s) під час завантаження %s [attempt %s/%s]",
                    code, img_url, attempt, self.max_attempts,
                    extra={"download_error": DownloadError.HTTP_STATUS.value, "http_status": code},
                )
            except Exception as exc:										# noqa: BLE001
                logger.warning(
                    "⚠️ Неочікувана помилка завантаження %s [attempt %s/%s]: %s",
                    img_url, attempt, self.max_attempts, exc,
                    extra={"download_error": DownloadError.UNKNOWN.value},
                )

            if attempt < self.max_attempts:
                delay = self._retry_delay(attempt)
                logger.debug("⏳ Наступна спроба %d через %.2f с.", attempt + 1, delay)
                await asyncio.sleep(delay)								# 😴 Робимо паузу перед наступною спробою

        logger.error(
            "❌ Не вдалося завантажити зображення після %s спроб: %s",
            self.max_attempts,
            img_url,
            extra={"download_error": DownloadError.HTTP_STATUS.value},
        )
        _inc_error(DownloadError.HTTP_STATUS.value)
        return DownloadError.HTTP_STATUS

    # ================================
    # 📦 СТРИМІНГ У ПАМ’ЯТЬ
    # ================================
    async def _stream_to_memory(
        self,
        response: httpx.Response,
        *,
        img_url: str,
        content_type: Optional[str],
    ) -> FetchOutcome:
        """📦 Зчитує байти відповіді в пам'ять з перевірками сигнатур."""
        hasher = hashlib.sha256()										# 🔐 Крок за кроком рахуємо SHA256
        buffer = bytearray()											# 📦 Буфер для байтів
        bytes_read = 0													# 🔢 Лічильник отриманих байтів
        first_chunk_checked = False										# 🧪 Чи перевіряли сигнатуру
        logger.debug("📥 Стримінг у пам'ять: %s (chunk=%d)", img_url, self.chunk_size)

        async for chunk in response.aiter_bytes(self.chunk_size):
            if not chunk:												# 🪹 Пропускаємо порожні шматки
                continue

            if self.verify_magic and not first_chunk_checked:
                first_chunk_checked = True								# ✅ Позначаємо, що сигнатуру перевірено
                magic_error = self._validate_magic(chunk, img_url)
                if magic_error:
                    return magic_error									# 🚫 Сигнатура не відповідає зображенню

            bytes_read += len(chunk)									# 🔢 Оновлюємо лічильник розміру
            if bytes_read > self.max_bytes:
                logger.error(
                    "❌ Перевищено ліміт розміру: %s B > %s B (%s)",
                    bytes_read,
                    self.max_bytes,
                    img_url,
                    extra={"download_error": DownloadError.TOO_LARGE.value, "bytes_read": bytes_read},
                )
                _inc_error(DownloadError.TOO_LARGE.value)
                return DownloadError.TOO_LARGE

            buffer += chunk												# 📦 Додаємо байти до буфера
            hasher.update(chunk)										# 🔐 Оновлюємо SHA256
            if bytes_read % (self.chunk_size * 10) == 0:
                logger.debug("📥 Зчитано %d байт із %s", bytes_read, img_url)

        if bytes_read == 0:
            logger.error("❌ Отримано порожню відповідь: %s", img_url, extra={"download_error": DownloadError.EMPTY_BODY.value})
            _inc_error(DownloadError.EMPTY_BODY.value)
            return DownloadError.EMPTY_BODY

        _inc_ok()
        logger.debug("📥 Завершили стримінг у пам'ять (%d байт).", bytes_read)
        return ImageData(												# 📦 Формуємо DTO для OCR
            url=img_url,
            content=bytes(buffer),
            sha256=hasher.hexdigest(),
            content_type=content_type,
        )

    # ================================
    # 💾 СТРИМІНГ НА ДИСК
    # ================================
    async def _stream_to_disk(
        self,
        response: httpx.Response,
        *,
        img_url: str,
        output_path: Path,
        content_type: Optional[str],
        content_length: Optional[int],
    ) -> DownloadOutcome:
        """💾 Записує байти у тимчасовий файл та замінює цільовий шлях атомарно."""
        output_path = output_path.resolve()								# 📁 Канонічний шлях для запису
        output_path.parent.mkdir(parents=True, exist_ok=True)			# 🧱 Переконуємося, що каталог існує
        logger.debug(
            "💾 Старт стримінгу на диск: %s (ct=%s, length=%s)",
            output_path,
            content_type or "n/a",
            content_length if content_length is not None else "n/a",
        )

        fd, tmp_name = tempfile.mkstemp(								# 🧪 Створюємо тимчасовий файл
            prefix=output_path.name + ".",
            suffix=".part",
            dir=str(output_path.parent),
        )
        os.close(fd)													# 🔐 Закриваємо файловий дескриптор
        tmp_path = Path(tmp_name)										# 📁 Представляємо шлях як Path

        hasher = hashlib.sha256() if self.compute_sha256 else None		# 🔐 За потреби рахуємо SHA256
        bytes_written = 0												# 🔢 Скільки байтів записано
        first_chunk_checked = False										# 🧪 Сигнатура перевірена?

        try:
            with tmp_path.open("wb") as file_handle:					# 💾 Пишемо у тимчасовий файл
                async for chunk in response.aiter_bytes(self.chunk_size):
                    if not chunk:
                        continue

                    if self.verify_magic and not first_chunk_checked:
                        first_chunk_checked = True
                        magic_error = self._validate_magic(chunk, img_url)
                        if magic_error:
                            return magic_error

                    bytes_written += len(chunk)
                    if bytes_written > self.max_bytes:
                        logger.error(
                            "❌ Перевищено ліміт розміру: %s B > %s B (%s)",
                            bytes_written,
                            self.max_bytes,
                            img_url,
                            extra={"download_error": DownloadError.TOO_LARGE.value, "bytes_written": bytes_written},
                        )
                        _inc_error(DownloadError.TOO_LARGE.value)
                        return DownloadError.TOO_LARGE

                    try:
                        file_handle.write(chunk)						# ✍️ Пишемо черговий шматок
                    except Exception:
                        logger.exception(
                            "❌ Помилка запису файлу: %s",
                            tmp_path,
                            extra={"download_error": DownloadError.IO_ERROR.value},
                        )
                        _inc_error(DownloadError.IO_ERROR.value)
                        return DownloadError.IO_ERROR

                    if hasher:
                        hasher.update(chunk)							# 🔐 Оновлюємо хеш
                    if bytes_written % (self.chunk_size * 10) == 0:
                        logger.debug("💾 Записано %d байт у %s", bytes_written, output_path)

            if bytes_written == 0:
                logger.error("❌ Отримано порожню відповідь: %s", img_url, extra={"download_error": DownloadError.EMPTY_BODY.value})
                _inc_error(DownloadError.EMPTY_BODY.value)
                return DownloadError.EMPTY_BODY

            try:
                os.replace(tmp_path, output_path)						# 🔁 Атомарно підміняємо файл
            except Exception:
                logger.exception(
                    "❌ Не вдалося замінити %s → %s",
                    tmp_path,
                    output_path,
                    extra={"download_error": DownloadError.IO_ERROR.value},
                )
                _inc_error(DownloadError.IO_ERROR.value)
                return DownloadError.IO_ERROR

        finally:
            if tmp_path.exists():										# 🧹 Прибираємо тимчасовий файл
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass												# 🤫 Файл уже видалено — нічого страшного

        sha_hex = hasher.hexdigest() if hasher else None				# 🔐 Фінальний SHA256
        logger.info(
            "✅ Зображення збережено: %s (%s B, %s)",
            output_path,
            bytes_written,
            content_type or "n/a",
            extra={
                "download_status": "ok",
                "bytes_written": bytes_written,
                "content_type": content_type or "n/a",
            },
        )
        _inc_ok()
        return DownloadResult(
            path=output_path,
            content_type=content_type,
            content_length=content_length,
            bytes_written=bytes_written,
            sha256=sha_hex,
        )

    # ================================
    # 🛡️ ДОПОМІЖНІ ПЕРЕВІРКИ
    # ================================
    def _ensure_status(self, response: httpx.Response, img_url: str, attempt: int) -> Optional[DownloadError]:
        """🛡️ Перевіряє, що HTTP-статус успішний."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            code = getattr(exc.response, "status_code", None)			# 🔢 Код статусу з відповіді
            logger.warning(
                "🌐 HTTP %s при завантаженні %s [attempt %s/%s]",
                code,
                img_url,
                attempt,
                self.max_attempts,
                extra={"download_error": DownloadError.HTTP_STATUS.value, "http_status": code},
            )
            _inc_error(DownloadError.HTTP_STATUS.value)
            return DownloadError.HTTP_STATUS
        return None

    def _normalize_ct(self, content_type: Optional[str]) -> Optional[str]:
        """🛠️ Нормалізує `Content-Type` (trim + lower)."""
        return content_type.lower().strip() if content_type else None	# 🧼 Повертаємо охайне значення

    def _parse_length(self, header_value: Optional[str]) -> Optional[int]:
        """📏 Перетворює заголовок `Content-Length` у int."""
        if not header_value or not header_value.isdigit():
            return None
        return int(header_value)

    def _validate_content_type(self, content_type: Optional[str], img_url: str) -> Optional[DownloadError]:
        """🛡️ Перевіряє `Content-Type` проти дозволених префіксів."""
        if content_type and any(content_type.startswith(prefix) for prefix in self.ct_prefixes):
            return None
        if content_type and not self.verify_magic:
            logger.error(
                "❌ Неприпустимий Content-Type (%s) для %s",
                content_type,
                img_url,
                extra={"download_error": DownloadError.NOT_IMAGE.value, "content_type": content_type},
            )
            _inc_error(DownloadError.NOT_IMAGE.value)
            return DownloadError.NOT_IMAGE
        return None

    def _validate_length(self, content_length: Optional[int], img_url: str) -> Optional[DownloadError]:
        """🛡️ Перевіряє розмір файлу за заголовком `Content-Length`."""
        if content_length is None or content_length <= self.max_bytes:
            return None
        logger.error(
            "❌ Файл %s перевищує ліміт: %s B > %s B",
            img_url,
            content_length,
            self.max_bytes,
            extra={"download_error": DownloadError.TOO_LARGE.value, "content_length": content_length},
        )
        _inc_error(DownloadError.TOO_LARGE.value)
        return DownloadError.TOO_LARGE

    def _validate_magic(self, first_chunk: bytes, img_url: str) -> Optional[DownloadError]:
        """🧪 Звіряє перший chunk із сигнатурами PNG/JPEG/GIF/WebP."""
        signature = first_chunk[:16]										# 🧾 Перші байти відповіді
        if signature.startswith(MAGIC_SIGNATURES[0][0]):					# 🟢 PNG
            return None
        if signature.startswith(MAGIC_SIGNATURES[1][0]):					# 🟢 JPEG
            return None
        if signature.startswith(MAGIC_SIGNATURES[2][0]):					# 🟢 GIF
            return None
        if (
            len(signature) >= 12											# 🟢 WebP: RIFF....WEBP
            and signature[:4] == MAGIC_SIGNATURES[3][0]
            and signature[8:12] == b"WEBP"
        ):
            return None

        logger.error(
            "❌ Сигнатура не схожа на зображення: %s",
            img_url,
            extra={"download_error": DownloadError.MAGIC_MISMATCH.value},
        )
        _inc_error(DownloadError.MAGIC_MISMATCH.value)
        return DownloadError.MAGIC_MISMATCH

    def _retry_delay(self, attempt: int) -> float:
        """⏳ Повертає затримку перед наступним ретраєм."""
        jitter = 0.1 * attempt											# 🎲 Легкий джиттер для уникнення піків
        return self.backoff_base_s * attempt + jitter					# 📊 Експоненційний backoff


__all__ = [
    "DownloadError",
    "DownloadOutcome",
    "DownloadResult",
    "ImageData",
    "ImageDownloader",
    "FetchOutcome",
]
