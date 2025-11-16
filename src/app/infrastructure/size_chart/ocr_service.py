# 🧠 app/infrastructure/size_chart/ocr_service.py
"""
🧠 OCR-сервіс для розпізнавання таблиць розмірів за допомогою OpenAI Vision.

🔹 Завантажує зображення (через `ImageDownloader`) та кешує результат за SHA256.
🔹 Використовує `PromptService` для побудови промтів під конкретні типи таблиць.
🔹 Повторює запити з експоненційним backoff та підтримує інструментарій метрик.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio															# ⏳ Обмеження часу та backoff
import base64															# 🖼️ Кодування зображень
import hashlib															# 🔐 Обчислення SHA256
import json															# 📦 Обробка JSON
import logging															# 🧾 Логування пайплайна
import os																# 📁 Робота з файловою системою
import random															# 🎲 Джиттер для backoff
import re																# 🔍 Витяг JSON із markdown
from pathlib import Path												# 🛤️ Шляхи кешу
from typing import Any, Dict, Final, Optional, cast					# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService					# ⚙️ Конфігурація сервісу
from app.infrastructure.ai.open_ai_serv import OpenAIService			# 🤖 Клієнт OpenAI
from app.infrastructure.ai.prompt_service import PromptService		# 💬 Побудова промтів
from app.infrastructure.size_chart.dto import SizeChartOcrResult, SizeChartOcrStatus  # 📊 DTO результатів
from app.infrastructure.size_chart.image_downloader import ImageData, ImageDownloader  # 📥 Завантаження зображень
from app.shared.utils.logger import LOG_NAME							# 🏷️ Ім'я базового логера
from app.shared.utils.prompt_service import ChartType					# 📊 Тип таблиці

logger = logging.getLogger(f"{LOG_NAME}.ocr")							# 🧾 Локальний логер OCR

# ================================
# 📊 МЕТРИКИ (ОПЦІЙНО)
# ================================
METRIC_SOURCE = "openai_vision"										# 📊 Значення label "source" для OCR подій

try:																	# 📈 Підключаємо метрики, якщо доступні
    from app.shared.metrics.ocr import (
        OCR_CACHE_HIT,
        OCR_CACHE_MISS,
        OCR_FAILURE,
        OCR_SUCCESS,
    )
except Exception:														# pragma: no cover
    OCR_SUCCESS = OCR_FAILURE = OCR_CACHE_HIT = OCR_CACHE_MISS = None


# ================================
# 🔧 УТИЛІТИ КОНФІГУРАЦІЇ
# ================================
def _cfg_float(cfg: ConfigService, key: str, default: float) -> float:
    """🔢 Безпечно читає float із конфігурації."""
    value = cfg.get(key, default, cast=float)							# 🛠️ Пробуємо отримати зі сховища
    try:
        return float(value) if value is not None else default			# 🔄 Приводимо до float
    except Exception:
        return default													# ♻️ Повертаємо дефолт при помилці


def _cfg_int(cfg: ConfigService, key: str, default: int) -> int:
    """🔢 Безпечно читає int із конфігурації."""
    value = cfg.get(key, default, cast=int)								# 🛠️ Отримуємо або дефолт
    try:
        return int(value) if value is not None else default				# 🔄 Перетворюємо на int
    except Exception:
        return default


def _cfg_str(cfg: ConfigService, key: str, default: str) -> str:
    """🔤 Повертає рядок, обрізаючи пробіли."""
    value = cfg.get(key, default, cast=str)								# 🛠️ Беремо значення
    try:
        cleaned = (value or default).strip()							# ✂️ Прибираємо пробіли
        return cleaned or default										# 🔁 Не дозволяємо порожні строки
    except Exception:
        return default


_JSON_BLOCK_RE: Final[re.Pattern[str]] = re.compile(					# 🧩 Шаблон для витягу JSON
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)


# ================================
# 🧠 ОСНОВНИЙ СЕРВІС OCR
# ================================
class OCRService:
    """🧠 Оркеструє OCR-розпізнавання зображень таблиць розмірів."""

    def __init__(
        self,
        openai_service: OpenAIService,
        prompt_service: PromptService,
        *,
        request_timeout_s: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_s: Optional[float] = None,
        downloader: Optional[ImageDownloader] = None,
        config: Optional[ConfigService] = None,
    ) -> None:
        self.openai_service = openai_service							# 🤖 API OpenAI Vision
        self.prompt_service = prompt_service							# 💬 Побудова промтів
        self.downloader = downloader or ImageDownloader()				# 📥 Асинхронний завантажувач
        self.cfg = config or ConfigService()							# ⚙️ Джерело конфігурацій

        # ⚙️ Таймаути та ретраї
        self.request_timeout_s = (
            float(request_timeout_s) if request_timeout_s is not None else _cfg_float(self.cfg, "ocr.request_timeout_s", 60.0)
        )																# ⏳ Граничний час на API-виклик
        self.max_retries = int(max_retries) if max_retries is not None else _cfg_int(self.cfg, "ocr.max_retries", 2)	# 🔁 Кількість повторів

        base_default = backoff_s if backoff_s is not None else _cfg_float(self.cfg, "ocr.backoff.base_s", 0.6)	# 🐢 Базова затримка
        self.backoff_base_s = max(0.0, float(base_default))				# 🧮 Забезпечуємо невід'ємність
        self.backoff_cap_s = max(0.0, _cfg_float(self.cfg, "ocr.backoff.cap_s", 8.0))	# 🛑 Максимальна затримка
        jitter_mode = _cfg_str(self.cfg, "ocr.backoff.jitter", "full").lower()	# 🎲 Тип джиттера
        self.backoff_jitter = jitter_mode if jitter_mode in {"full", "equal", "none"} else "full"	# 🔧 Валідація режиму

        cache_dir_raw = (
            _cfg_str(self.cfg, "ocr.cache_dir", "")
            or _cfg_str(self.cfg, "files.ocr_cache_dir", "")
            or "./var/ocr_cache"
        )																# 📁 Шлях до кешу
        self.cache_dir = Path(cache_dir_raw).resolve()					# 🛤️ Абсолютний шлях
        self.cache_dir.mkdir(parents=True, exist_ok=True)				# 🧱 Гарантуємо існування каталогу
        logger.debug(
            "⚙️ OCRService init timeout=%.1fs retries=%d backoff_base=%.2fs cap=%.2fs jitter=%s cache=%s",
            self.request_timeout_s,
            self.max_retries,
            self.backoff_base_s,
            self.backoff_cap_s,
            self.backoff_jitter,
            self.cache_dir,
        )

    # ================================
    # 🌐 ПУБЛІЧНИЙ API
    # ================================
    async def recognize_url(self, image_url: str, size_chart_type: ChartType) -> SizeChartOcrResult:
        """🌐 Завантажує зображення за URL, виконує OCR та повертає результат."""
        logger.info("🔍 OCR(url): %s | type=%s", image_url, getattr(size_chart_type, "value", size_chart_type))
        image: ImageData = await self.downloader.fetch(image_url)		# 📥 Скачане зображення з SHA256
        logger.debug(
            "📥 Завантажено URL %s (bytes=%d, sha256=%s…)", image_url, len(image.content), image.sha256[:12]
        )
        return await self._recognize_bytes(
            image_bytes=image.content,
            sha256=image.sha256,
            size_chart_type=size_chart_type,
        )

    async def recognize(self, image_path: str, size_chart_type: ChartType) -> SizeChartOcrResult:
        """📁 Читає локальний файл, обчислює SHA256 та запускає OCR."""
        logger.info("🔍 OCR(file): %s | type=%s", image_path, getattr(size_chart_type, "value", size_chart_type))
        try:
            with open(image_path, "rb") as file_handle:
                file_bytes = file_handle.read()						# 💾 Зчитуємо байти файлу
        except Exception as exc:										# noqa: BLE001
            message = f"io_error: {exc}"
            logger.error("❌ Неможливо прочитати файл зображення: %s", exc, exc_info=True)
            return SizeChartOcrResult(status=SizeChartOcrStatus.IO_ERROR, error=message)

        sha256_hex = hashlib.sha256(file_bytes).hexdigest()			# 🔐 Обчислюємо SHA256 для кешу
        logger.debug("📁 Локальний файл %s зчитано (%d байт, sha256=%s…)", image_path, len(file_bytes), sha256_hex[:12])
        return await self._recognize_bytes(
            image_bytes=file_bytes,
            sha256=sha256_hex,
            size_chart_type=size_chart_type,
        )

    # ================================
    # 🧩 ОСНОВНИЙ ПАЙПЛАЙН
    # ================================
    async def _recognize_bytes(
        self,
        *,
        image_bytes: bytes,
        sha256: str,
        size_chart_type: ChartType,
    ) -> SizeChartOcrResult:
        """🧩 Обробляє байти зображення з кешем та ретраями."""
        cached = await self._load_from_cache(sha256)					# 📦 Перевіряємо кеш
        if cached:
            if OCR_CACHE_HIT:
                OCR_CACHE_HIT.labels(source="sha256").inc()
            logger.info("📦 OCR cache HIT (%s, status=%s)", sha256, cached.status.value)
            return cached

        if OCR_CACHE_MISS:
            OCR_CACHE_MISS.labels(source="sha256").inc()
        logger.info("📦 OCR cache MISS (%s)", sha256)

        prompt = self.prompt_service.size_chart(chart_type=size_chart_type)	# 💬 Підбираємо промт
        # 🔢 Обчислюємо загальну довжину всіх повідомлень у промті
        prompt_len = (
            sum(len(msg.content) for msg in prompt.messages)
            if prompt and hasattr(prompt, "messages")
            else 0
        )
        logger.debug(
            "💬 Сформовано промт для %s (len=%d символів).",
            size_chart_type.value,
            prompt_len,
        )
        attempt = 0															# 🔢 Лічильник спроб
        last_error: Optional[str] = None										# 🧾 Остання помилка
        response_text: Optional[str] = None									# 🧾 Сирий текст відповіді

        while attempt <= self.max_retries:
            attempt += 1
            logger.debug("🚀 OCR attempt %d/%d (sha=%s…)", attempt, self.max_retries + 1, sha256[:12])
            try:
                encoded_image = base64.b64encode(image_bytes).decode("utf-8")	# 🖼️ Готуємо base64
                response_text = await asyncio.wait_for(						# ⏳ Обмежуємо час виклику
                    cast(OpenAIService, self.openai_service).chat_completion_with_vision(
                        prompt=prompt,
                        image_base64=encoded_image,
                    ),
                    timeout=self.request_timeout_s,
                )

                if not response_text:
                    last_error = "empty_response"
                    logger.warning("⚠️ OCR повернув порожню відповідь (attempt %s)", attempt)
                    raise ValueError("Empty vision response")

                payload_text = self._extract_json_payload(response_text)	# 🧹 Витягуємо JSON
                logger.debug("🧾 OCR payload (sample): %s", payload_text[:200])
                payload_json = json.loads(payload_text)					# 📦 Перетворюємо в dict

                result = SizeChartOcrResult(								# ✅ Формуємо успішний результат
                    status=SizeChartOcrStatus.OK,
                    data=payload_json,
                    raw_text=response_text,
                )
                await self._save_to_cache(sha256, result)				# 💾 Зберігаємо у кеш
                if OCR_SUCCESS:
                    OCR_SUCCESS.labels(source=METRIC_SOURCE).inc()
                return result

            except asyncio.TimeoutError:
                last_error = "timeout"
                logger.warning("⏳ OCR timeout (attempt %s/%s)", attempt, self.max_retries)
            except json.JSONDecodeError as exc:
                last_error = "invalid_json"
                logger.error("❌ Некоректний JSON від OCR: %s", exc, extra={"response_sample": response_text[:200] if response_text else ""})
            except Exception as exc:										# noqa: BLE001
                last_error = str(exc)
                logger.exception("❌ Помилка OCR (attempt %s/%s): %s", attempt, self.max_retries, exc)

            if attempt <= self.max_retries:
                logger.debug("😴 Плануємо відкладення перед наступною спробою (attempt %d).", attempt + 1)
                await self._sleep_with_backoff(attempt)					# 😴 Чекаємо перед наступною спробою

        if OCR_FAILURE:
            OCR_FAILURE.labels(source=METRIC_SOURCE, reason=last_error or "unknown").inc()
        logger.error("❌ OCR завершився невдачею після %d спроб (sha=%s, reason=%s)", self.max_retries + 1, sha256, last_error)
        return SizeChartOcrResult(status=SizeChartOcrStatus.API_ERROR, error=last_error or "unknown")

    # ================================
    # 💾 РОБОТА З КЕШЕМ
    # ================================
    async def _load_from_cache(self, sha256: str) -> Optional[SizeChartOcrResult]:
        """💾 Повертає результат з кешу, якщо файл існує."""
        cache_path = self.cache_dir / f"{sha256}.json"					# 📁 Очікуваний шлях
        if not cache_path.exists():
            logger.debug("📦 Кеш-файл відсутній (%s).", cache_path)
            return None
        try:
            cache_text = cache_path.read_text(encoding="utf-8")			# 📖 Зчитуємо кешований JSON
            payload = json.loads(cache_text)							# 📦 Перетворюємо в dict
            status_raw = payload.get("status", SizeChartOcrStatus.API_ERROR.value)	# 🏷️ Стан у кеші
            try:
                status_enum = SizeChartOcrStatus(status_raw)			# 🔄 Перетворюємо на Enum
            except ValueError:
                status_enum = SizeChartOcrStatus.API_ERROR				# ❗ Фолбек при невідомому статусі
            logger.debug("📦 Кеш прочитано (%s, status=%s).", cache_path, status_enum.value)
            return SizeChartOcrResult(
                status=status_enum,
                data=payload.get("data"),
                raw_text=payload.get("raw_text"),
                error=payload.get("error"),
            )
        except Exception as exc:											# noqa: BLE001
            logger.warning("⚠️ Не вдалося прочитати кеш %s: %s", cache_path, exc)
            try:
                cache_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

    async def _save_to_cache(self, sha256: str, result: SizeChartOcrResult) -> None:
        """💾 Зберігає результат у кеш (ігнорує помилки запису)."""
        cache_path = self.cache_dir / f"{sha256}.json"					# 📁 Шлях кешу
        payload = {
            "status": result.status.value,
            "data": result.data,
            "raw_text": result.raw_text,
            "error": result.error,
        }																# 📦 Серіалізований словник
        tmp_path = cache_path.with_suffix(".json.part")					# 🧪 Тимчасовий файл
        try:
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp_path, cache_path)							# 🔁 Атомарний запис
            logger.debug("💾 OCR-кеш оновлено (%s).", cache_path)
        except Exception as exc:											# noqa: BLE001
            logger.warning("⚠️ Не вдалося зберегти кеш %s: %s", cache_path, exc)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    # ================================
    # 🧼 ОБРОБКА ВІДПОВІДІ
    # ================================
    def _extract_json_payload(self, response_text: str) -> str:
        """🧼 Дістає JSON-блок із відповіді GPT (між ```json ... ```)."""
        if not response_text:
            raise ValueError("Empty OCR response")
        match = _JSON_BLOCK_RE.search(response_text)
        if match:
            return match.group(1).strip()
        return response_text.strip()

    async def _sleep_with_backoff(self, attempt: int) -> None:
        """😴 Засинання із врахуванням backoff та джиттера."""
        base_delay = min(self.backoff_base_s * (2 ** (attempt - 1)), self.backoff_cap_s or float("inf"))	# 📊 Експоненційний backoff
        if self.backoff_jitter == "none":
            jitter = 0.0
        elif self.backoff_jitter == "equal":
            jitter = base_delay
        else:
            jitter = random.uniform(0, base_delay)						# 🎲 Повний джиттер
        delay = base_delay + jitter
        logger.debug("⏱️ Backoff sleep: base=%.2fs jitter=%.2fs total=%.2fs (attempt=%d).", base_delay, jitter, delay, attempt)
        await asyncio.sleep(delay)										# 😴 Чекаємо перед наступною спробою


__all__ = ["OCRService"]
