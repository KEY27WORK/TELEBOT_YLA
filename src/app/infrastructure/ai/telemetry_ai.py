# 📬 app/infrastructure/ai/telemetry_ai.py
"""
📬 Легковагова телеметрія для AI-викликів.

🔹 Маскує чутливі дані у промптах та відповідях перед логуванням.
🔹 Пише події у JSONL-файл і (опційно) транслює їх через спільний логер.
🔹 Рахує приблизну вартість запиту, щоб відстежувати витрати.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (зовнішніх залежностей немає)											# 🚫 Використовуємо лише stdlib

# 🔠 Системні імпорти
import json															# 🧾 Серіалізація подій
import logging														# 🪵 Логування дій
import os																# 📁 Робота з файловою системою
import re																# ✂️ Маскування даних
import time															# ⏱️ Таймінги викликів
import uuid															# 🆔 Кореляційні ідентифікатори
from dataclasses import asdict, dataclass								# 🧱 DTO для подій
from pathlib import Path												# 📂 Підготовка директорій
from typing import Any, Dict, Optional								# 📐 Типові анотації

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService					# ⚙️ Джерело конфігів
from app.shared.utils.logger import LOG_NAME							# 🏷️ Базове імʼя логера


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai.telemetry")				# 🧾 Виділений логер підсистеми


# ================================
# 🛡️ ПРАВИЛА МАСКУВАННЯ
# ================================
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")	# 📧 Шаблон e-mail
_PHONE_RE = re.compile(r"\+?\d[\d\-\s()]{7,}\d")						# ☎️ Телефонні номери
_URL_RE = re.compile(r"https?://[^\s)>\]]+")							# 🔗 URL-адреси
_NUMSEQ_RE = re.compile(r"\b\d{6,}\b")									# 🔢 Довгі числові послідовності


# ================================
# 🔧 ДОПОМІЖНІ ФУНКЦІЇ МАСКУВАННЯ
# ================================
def _mask_text(source: str) -> str:
    """🔧 Послідовно замінює чутливі патерни технічними маркерами."""
    masked = _EMAIL_RE.sub("[email]", source)							# 📧 Ховаємо e-mail
    masked = _PHONE_RE.sub("[phone]", masked)							# ☎️ Ховаємо телефони
    masked = _URL_RE.sub("[url]", masked)								# 🔗 Ховаємо URL
    masked = _NUMSEQ_RE.sub("[num]", masked)							# 🔢 Ховаємо довгі числа
    logger.debug("🛡️ Mask applied", extra={"before_len": len(source), "after_len": len(masked)})  # 🪵 Діагностика маскування
    return masked														# ↩️ Повертаємо маскований текст


def _maybe_mask(value: Optional[str], enabled: bool) -> Optional[str]:
    """🔁 Повертає маскований рядок, якщо опція увімкнена."""
    if not value:														# 🚫 Немає що маскувати
        return value													# ↩️ Повертаємо як є
    return _mask_text(value) if enabled else value						# 🔀 Обираємо сценарій


# ================================
# 📏 ПІДРАХУНКИ Й ЕКОНОМІКА
# ================================
def _char_count(text: Optional[str]) -> int:
    """🔢 Рахує кількість символів у рядку (None → 0)."""
    count = len(text or "")											# 🔢 Безпечний підрахунок
    logger.debug("🧮 Counted chars", extra={"count": count})			# 🪵 Фіксуємо довжину
    return count														# ↩️ Повертаємо результат


def _read_model_prices(cfg: ConfigService) -> Dict[str, Any]:
    """💰 Зчитує налаштування тарифів моделей з конфігів."""
    prices_node = cfg.get("openai.prices")								# 💾 Основне джерело
    if isinstance(prices_node, dict):									# ✅ Є окремий розділ
        logger.debug("💰 Prices loaded from openai.prices", extra={"models": list(prices_node.keys())})
        return prices_node												# ↩️ Повертаємо словник
    weights_node = cfg.get("weights")									# 🔁 Фолбек на weights.json
    if isinstance(weights_node, dict):
        logger.debug("💰 Prices loaded from weights", extra={"models": list(weights_node.keys())})
        return weights_node												# ↩️ Повертаємо фолбек
    logger.debug("⚠️ Prices not configured")							# 🪵 Немає конфігів
    return {}															# ↩️ Порожній словник


def _estimate_cost_usd(
    model: str,
    prompt_chars: int,
    resp_chars: int,
    prices: Dict[str, Any],
) -> Optional[float]:
    """💵 Оцінює вартість запиту (дуже приблизно, ~chars/4 → токени)."""
    model_prices = prices.get(model)									# 🔍 Беремо конфіг моделі
    if not isinstance(model_prices, dict):								# 🚫 Немає даних по моделі
        logger.debug("⚠️ No pricing for model", extra={"model": model})
        return None													# ↩️ Не повертаємо значення
    input_price = float(model_prices.get("input_per_1k", 0.0))			# 💵 Тариф за вхідні токени
    output_price = float(model_prices.get("output_per_1k", 0.0))		# 💵 Тариф за вихідні токени
    input_tokens = prompt_chars / 4.0									# 🔢 Оцінка токенів промпту
    output_tokens = resp_chars / 4.0									# 🔢 Оцінка токенів відповіді
    estimation = round(
        (input_tokens / 1000.0) * input_price
        + (output_tokens / 1000.0) * output_price,
        6,
    )																	# 🧮 Фінальна вартість
    logger.debug(
        "💵 Cost estimated",
        extra={
            "model": model,
            "prompt_chars": prompt_chars,
            "response_chars": resp_chars,
            "usd": estimation,
        },
    )																	# 🪵 Діагностичний лог
    return estimation													# ↩️ Повертаємо оцінку


# ================================
# 🧱 DTO ПОДІЇ
# ================================
@dataclass(slots=True)
class AITelemetryEvent:
    """🧾 Структура запису у JSONL-файл телеметрії."""

    corr_id: str														# 🆔 Кореляційний ідентифікатор
    provider: str														# 🏢 Постачальник AI
    model: str															# 🤖 Модель
    kind: str															# 🧠 Тип виклику ("chat"/"vision")
    status: str															# 📊 "ok" або "error"
    started_ts: float													# ⏱️ Час старту
    latency_ms: int														# ⌛ Тривалість у мс
    prompt_chars: int													# 🔢 К-ть символів у промпті
    response_chars: int													# 🔢 К-ть символів у відповіді
    input_image_count: int												# 🖼️ К-ть зображень у вхідних даних
    error: Optional[str] = None											# ⚠️ Текст помилки (якщо є)
    cost_usd: Optional[float] = None									# 💵 Оцінена вартість
    prompt_preview: Optional[str] = None								# 🛡️ Обрізаний промпт
    response_preview: Optional[str] = None								# 🛡️ Обрізана відповідь


# ================================
# 🗂️ СИНК ЗАПИСУ ТЕЛЕМЕТРІЇ
# ================================
class TelemetrySink:
    """🗂️ Пише події телеметрії у файл і (опційно) у stdout."""

    def __init__(self, cfg: ConfigService) -> None:
        self._cfg = cfg													# ⚙️ Конфігураційний сервіс
        defaults_path = "var/telemetry/ai.jsonl"						# 📁 Шлях за замовчуванням
        node = self._cfg.get("telemetry.ai", {}) or {}					# 🧾 Блок конфігурації
        self.enabled = bool(node.get("enabled", True))					# 🔛 Чи активна телеметрія
        self.mask_prompts = bool(node.get("mask_prompts", True))		# 🛡️ Чи маскувати тексти
        self.stdout = bool(node.get("stdout", False))					# 📣 Чи дублювати у лог
        self.path = str(node.get("path", defaults_path))				# 📁 Фінальний шлях файлу
        logger.info(
            "🗂️ telemetry.sink_init",
            extra={
                "enabled": self.enabled,
                "path": self.path,
                "stdout": self.stdout,
            },
        )																# 🪵 Фіксуємо параметри
        if self.enabled and self.path:									# ✅ Потрібно готувати директорію
            try:
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)  # 🗂️ Створюємо директорію
                logger.debug("🗂️ telemetry.path_ready", extra={"path": self.path})
            except Exception as exc:									# noqa: BLE001 # 🚨 Проблема з FS
                logger.warning(
                    "⚠️ telemetry.path_init_failed",
                    extra={"path": self.path, "error": str(exc)},
                )														# 🪵 Попереджаємо, але не падаємо

    def write(self, event: AITelemetryEvent) -> None:
        """📝 Зберігає подію телеметрії у файл/лог."""
        if not self.enabled:											# 🚫 Телеметрія вимкнена
            logger.debug("⚠️ telemetry.write_skipped_disabled")
            return														# ↩️ Нічого не робимо
        payload = asdict(event)										# 🧾 Конвертуємо у словник
        line = json.dumps(payload, ensure_ascii=False)					# 📝 Готуємо JSON-рядок
        if self.path:													# 📁 Пишемо у файл, якщо шлях задано
            try:
                with open(self.path, "a", encoding="utf-8") as file:	# 📂 Відкриваємо файл у режимі append
                    file.write(line + os.linesep)						# 📝 Додаємо рядок
                logger.debug(
                    "📝 telemetry.event_written",
                    extra={"path": self.path, "corr_id": event.corr_id},
                )														# 🪵 Фіксуємо запис
            except Exception as exc:									# noqa: BLE001 # 🚨 Помилка запису
                logger.warning(
                    "⚠️ telemetry.file_write_failed",
                    extra={"path": self.path, "error": str(exc)},
                    exc_info=True,
                )														# 🪵 Лог для розслідування
        if self.stdout:												# 📣 Дублюємо у stdout/лог
            logger.info("AI_TELEMETRY %s", line)						# 🪵 Структурований лог

    def event(self, name: str, payload: Dict[str, Any]) -> None:
        """🗒️ Фіксує сервісну подію (не виклик моделі)."""
        if not self.enabled:											# 🚫 Телеметрія вимкнена
            logger.debug("⚠️ telemetry.service_event_skipped")
            return														# ↩️ Пропускаємо
        entry = {
            "ts": time.time(),											# ⏱️ Час події
            "type": "service",											# 🏷️ Тип запису
            "name": name,												# 🧾 Назва події
            "payload": payload,											# 📦 Додаткові дані
        }																# 🧱 Формуємо структуру
        line = json.dumps(entry, ensure_ascii=False)					# 📝 Перетворюємо у JSON
        if self.path:													# 📁 Запис у файл
            try:
                with open(self.path, "a", encoding="utf-8") as file:	# 📂 Append-мод
                    file.write(line + os.linesep)						# 📝 Кладемо рядок
                logger.debug(
                    "🗒️ telemetry.service_event_written",
                    extra={"path": self.path, "name": name},
                )														# 🪵 Фіксуємо успіх
            except Exception as exc:									# noqa: BLE001
                logger.warning(
                    "⚠️ telemetry.service_write_failed",
                    extra={"path": self.path, "error": str(exc)},
                    exc_info=True,
                )														# 🪵 Репорт про збій
        if self.stdout:												# 📣 Дублюємо у лог
            logger.info("AI_SERVICE %s", line)							# 🪵 Відокремлений тег


# ================================
# 🧠 КОНТЕКСТ ТЕЛЕМЕТРІЇ
# ================================
class AITelemetry:
    """
    🧠 Контекст-менеджер, що фіксує час виконання, статус і витрати AI-виклику.

    Використання:
        with AITelemetry("openai", model, "chat", prompt_text, sink) as telemetry:
            ... виклик моделі ...
            telemetry.set_response_text(text)
            telemetry.ok()
    """

    def __init__(
        self,
        provider: str,
        model: str,
        kind: str,
        prompt_text: Optional[str],
        sink: TelemetrySink,
        *,
        config_service: Optional[ConfigService] = None,
    ) -> None:
        self.provider = provider										# 🏢 Постачальник
        self.model = model												# 🤖 Модель
        self.kind = kind												# 🧠 Тип виклику
        self.prompt_text = prompt_text or ""							# 📝 Промпт (може бути None)
        self.sink = sink												# 🗂️ Приймач телеметрії
        self.corr_id = uuid.uuid4().hex								# 🆔 Генеруємо ID
        self.started = time.time()										# ⏱️ Фіксуємо старт
        self.prompt_chars = _char_count(self.prompt_text)				# 🔢 Лічимо символи промпту
        self.response_text: Optional[str] = None						# 📄 Відповідь моделі
        self.input_image_count = 0										# 🖼️ К-ть зображень у вхідних даних
        self.status = "ok"												# ✅ Статус за замовчуванням
        self.error: Optional[str] = None								# ⚠️ Текст помилки
        cfg = config_service or ConfigService()						# ⚙️ Використовуємо переданий або новий сервіс
        self._prices_cache = _read_model_prices(cfg)					# 💰 Кеш тарифів для оцінки
        logger.debug(
            "🧠 telemetry.context_init",
            extra={"corr_id": self.corr_id, "model": model, "kind": kind},
        )																# 🪵 Фіксуємо запуск контексту

    # ================================
    # ⚙️ КОНФІГУРУВАННЯ КОНТЕКСТУ
    # ================================
    def set_input_image_count(self, count: int) -> None:
        """🖼️ Фіксує кількість зображень у вхідному запиті."""
        self.input_image_count = max(0, int(count))					# 🔢 Нормалізуємо значення
        logger.debug(
            "🖼️ telemetry.images_set",
            extra={"corr_id": self.corr_id, "count": self.input_image_count},
        )																# 🪵 Діагностика

    def set_response_text(self, text: Optional[str]) -> None:
        """📝 Зберігає відповідь моделі для подальшого логування."""
        self.response_text = text										# 📝 Фіксуємо відповідь
        logger.debug(
            "📝 telemetry.response_set",
            extra={
                "corr_id": self.corr_id,
                "has_text": bool(text),
            },
        )																# 🪵 Чи є текст

    def ok(self) -> None:
        """✅ Позначає виклик як успішний."""
        self.status = "ok"												# ✅ Статус успіху
        logger.debug("✅ telemetry.mark_ok", extra={"corr_id": self.corr_id})  # 🪵 Фіксуємо стан

    def fail(self, error: str) -> None:
        """❌ Позначає виклик як невдалий і зберігає причину."""
        self.status = "error"											# ❌ Статус помилки
        self.error = error												# ⚠️ Текст помилки
        logger.debug(
            "❌ telemetry.mark_error",
            extra={"corr_id": self.corr_id, "error": error},
        )																# 🪵 Фіксуємо збій

    # ================================
    # 🔁 КОНТЕКСТ-МЕНЕДЖЕР
    # ================================
    def __enter__(self) -> "AITelemetry":
        """🔁 Повертає себе для використання у `with`."""
        return self													# ↩️ Контекст

    def __exit__(self, exc_type, exc, tb) -> None:
        """📤 На виході формує та надсилає подію телеметрії."""
        if exc is not None:											# ⚠️ Виклик завершився винятком
            self.fail(str(exc))										# ❌ Фіксуємо помилку
        response_chars = _char_count(self.response_text)				# 🔢 Рахуємо символи відповіді
        latency_ms = int((time.time() - self.started) * 1000)			# ⏱️ Обчислюємо затримку
        mask_enabled = self.sink.mask_prompts							# 🛡️ Чи маскуємо тексти
        prompt_preview = (
            _maybe_mask(self.prompt_text[:500], mask_enabled) if self.prompt_text else None
        )																# 🛡️ Обрізаний промпт
        response_preview = (
            _maybe_mask((self.response_text or "")[:500], mask_enabled) if self.response_text else None
        )																# 🛡️ Обрізана відповідь
        cost = _estimate_cost_usd(self.model, self.prompt_chars, response_chars, self._prices_cache)  # 💵 Оцінка
        event = AITelemetryEvent(
            corr_id=self.corr_id,
            provider=self.provider,
            model=self.model,
            kind=self.kind,
            status=self.status,
            started_ts=self.started,
            latency_ms=latency_ms,
            prompt_chars=self.prompt_chars,
            response_chars=response_chars,
            input_image_count=self.input_image_count,
            error=self.error,
            cost_usd=cost,
            prompt_preview=prompt_preview,
            response_preview=response_preview,
        )																# 🧱 Готуємо DTO
        logger.debug(
            "📤 telemetry.event_ready",
            extra={"corr_id": self.corr_id, "latency_ms": latency_ms},
        )																# 🪵 Підтверджуємо готовність
        try:
            self.sink.write(event)									# 📝 Записуємо подію
        except Exception as exc:										# noqa: BLE001 # 🚨 Помилка запису
            logger.warning(
                "⚠️ telemetry.write_failed",
                extra={"corr_id": self.corr_id, "error": str(exc)},
                exc_info=True,
            )															# 🪵 Репорт про збій


__all__ = ["AITelemetryEvent", "TelemetrySink", "AITelemetry"]			# 📦 Експортований API
