# 📬 app/infrastructure/ai/ai_task_service.py
"""
📬 Вискорівневий сервіс AI-завдань (вага, переклад, слогани).

🔹 Ділегує виклики OpenAI через наші `PromptService` та `OpenAIService`.
🔹 Має локальний TTL-кеш для перекладів з опційною файловою прослойкою.
🔹 ЕмІтує сервісні телеметричні події та логує всі ключові кроки.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (зовнішніх залежностей немає)										# 🚫 Використовуємо stdlib

# 🔠 Системні імпорти
import hashlib														# 🔐 Формування ключів кешу
import json															# 📄 Збереження кешу на диск
import logging														# 🧾 Логування
import re															# 🔤 Нормалізація заголовків секцій
import time															# ⏱️ TTL та статистика
from pathlib import Path											# 📂 Робота з директоріями кешу
from typing import Any, Dict, Optional, Sequence, Tuple			# 📐 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService				# ⚙️ Читання конфігів
from app.domain.ai.task_contracts import (							# 🤝 Контракти домену
    IBannerPostGenerator,
    ISloganGenerator,
    ITranslator,
    IWeightEstimator,
)
from app.shared.utils.logger import LOG_NAME						# 🏷️ Базовий логер
from .open_ai_serv import OpenAIService								# 🤖 Робота з OpenAI API
from .prompt_service import PromptService							# ✏️ Побудова промптів
from .telemetry_ai import TelemetrySink								# 📈 Телеметрія сервісу


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai.tasks")					# 🧾 Іменований логер

DEFAULT_SLOGAN = "YoungLA вайб, твій щоденний драйв 🚀"				# 🪄 Fallback для слоганів
DEFAULT_BANNER_POST = (
    "❗️YoungLA drop вже на головній! Забирай свій сет та замовляй доставку по Україні просто зараз. "
    "#youngla #younglaua #дроп #gymwear #стрітстайл"
)																	# 🪧 Fallback caption


# ================================
# 🔒 TTL-КЕШ З ОПЦІЙНОЮ ПЕРСИСТЕНЦІЄЮ
# ================================
class _TTLCache:
    """🔒 Простий TTL-кеш із in-memory LRU та файловим шаром."""

    def __init__(self, max_items: int, ttl_sec: int, persist_dir: Optional[Path] = None) -> None:
        self._max = int(max_items)									# 📦 Максимальна кількість елементів
        self._ttl = int(ttl_sec)									# ⏱️ Життя елементу у секундах
        self._mem: Dict[str, Tuple[float, Any]] = {}				# 🧠 In-memory кеш: key -> (expires_at, value)
        self._order: Dict[str, float] = {}							# 🧮 LRU-індекс: key -> last_used_ts
        self._dir = persist_dir										# 📂 Директорія для файлів кешу
        if self._dir:
            self._dir.mkdir(parents=True, exist_ok=True)				# 🏗️ Готуємо директорію
            logger.debug("🗂️ cache.persist_dir_ready", extra={"path": str(self._dir)})

    @staticmethod
    def _now() -> float:
        """⏱️ Поточний час у секундах."""
        current_ts = time.time()										# ⏱️ Фіксуємо момент виклику
        return current_ts

    def _touch(self, key: str) -> None:
        """♻️ Оновлює timestamp використання ключа."""
        self._order[key] = self._now()									# 🔁 LRU-штамп для ключа

    def _evict_if_needed(self) -> None:
        """🧹 Виселяє найстаріші записи, якщо кеш переповнений."""
        if len(self._mem) <= self._max:									# ✅ Немає перевищення
            return
        overflow = max(1, len(self._mem) - self._max)				# 🧮 Скільки потрібно видалити
        victims = sorted(self._order.items(), key=lambda kv: kv[1])[:overflow]  # 🧾 LRU-список
        for victim, _ in victims:										# 🔁 Виселяємо найстаріших
            self._mem.pop(victim, None)								# ❌ Видаляємо з памʼяті
            self._order.pop(victim, None)							# ❌ Видаляємо з LRU
            logger.debug("🧹 cache.evict", extra={"key": victim})

    # ---------- ФАЙЛОВИЙ ШАР ----------
    def _disk_path(self, key: str) -> Optional[Path]:
        """📁 Повертає шлях до файлу кешу або None, якщо персистенція вимкнена."""
        if not self._dir:
            return None
        safe_key = key.replace("/", "_")							# 🛡️ Уникаємо вкладених директорій
        return self._dir / f"{safe_key}.json"

    def _disk_get(self, key: str) -> Optional[Any]:
        """📖 Пробує зчитати значення з диску."""
        path = self._disk_path(key)
        if not path or not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)							# 🧾 Читаємо JSON
            expires_at = float(payload.get("expires_at", 0))
            if self._now() > expires_at:
                path.unlink(missing_ok=True)							# ⏱️ Запис протерміновано
                logger.debug("⌛ cache.disk_expired", extra={"key": key})
                return None
            logger.debug("📖 cache.disk_hit", extra={"key": key})
            return payload.get("value")
        except Exception as exc:										# noqa: BLE001
            logger.warning("⚠️ cache.disk_read_failed", extra={"key": key, "error": str(exc)})
            return None

    def _disk_set(self, key: str, value: Any, expires_at: float) -> None:
        """💾 Записує значення на диск (якщо увімкнено персистенцію)."""
        path = self._disk_path(key)
        if not path:
            return
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump({"expires_at": expires_at, "value": value}, handle, ensure_ascii=False)
            logger.debug("💾 cache.disk_write", extra={"key": key})
        except Exception as exc:										# noqa: BLE001
            logger.warning("⚠️ cache.disk_write_failed", extra={"key": key, "error": str(exc)})

    # ---------- ПУБЛІЧНИЙ API ----------
    def get(self, key: str) -> Optional[Any]:
        """🔍 Повертає значення з кешу або None."""
        hit = self._mem.get(key)										# 🔎 Шукаємо в памʼяті
        now = self._now()												# ⏱️ Поточний час
        if hit:
            expires_at, value = hit										# 🧾 Розпаковуємо запис
            if now <= expires_at:										# ✅ Ще валідний
                self._touch(key)										# ♻️ Оновлюємо LRU
                logger.debug("🟢 cache.mem_hit", extra={"key": key})
                return value											# ↩️ Віддаємо зі швидкого кешу
            self._mem.pop(key, None)								# ⌛ Протерміновано
            self._order.pop(key, None)
            logger.debug("⌛ cache.mem_expired", extra={"key": key})

        disk_value = self._disk_get(key)								# 💾 Пробуємо диск
        if disk_value is not None:
            self.set(key, disk_value)								# 🔁 Прогріваємо in-memory
            return disk_value											# ↩️ Повертаємо з диску
        logger.debug("⚪ cache.miss", extra={"key": key})
        return None

    def set(self, key: str, value: Any) -> None:
        """📝 Зберігає значення у кеш (з оновленням LRU та диску)."""
        expires_at = self._now() + self._ttl							# ⏱️ Розрахунок часу життя
        self._mem[key] = (expires_at, value)							# 🧠 Зберігаємо в памʼяті
        self._touch(key)												# ♻️ Оновлюємо LRU
        self._evict_if_needed()											# 🧹 Контролюємо розмір
        self._disk_set(key, value, expires_at)							# 💾 Синхронізуємо на диск
        logger.debug("📝 cache.mem_store", extra={"key": key})


# ================================
# 🧠 СЕРВІС AI-ЗАВДАНЬ
# ================================
class AITaskService(IWeightEstimator, ITranslator, ISloganGenerator, IBannerPostGenerator):
    """🧠 Реалізація доменних контрактів для AI-перекладів/ваги/слоганів."""

    def __init__(
        self,
        openai_service: OpenAIService,
        prompts: PromptService,
        cfg: Optional[ConfigService] = None,
    ) -> None:
        self._openai = openai_service									# 🤖 Клієнт OpenAI
        self._prompts = prompts										# ✏️ Генерація промптів
        self._cfg = cfg or ConfigService()							# ⚙️ Конфіги (fallback)
        self._telemetry = TelemetrySink(self._cfg)					# 📈 Телеметрія сервісу

        cache_cfg = self._cfg.get("openai.cache", {}) or {}			# ⚙️ Налаштування кешу
        enabled = bool(cache_cfg.get("enabled", True))
        ttl_hours = int(cache_cfg.get("ttl_hours", 720))
        max_items = int(cache_cfg.get("max_items", 1000))
        persist_dir_raw = cache_cfg.get("persist_dir")
        persist_dir = Path(persist_dir_raw) if persist_dir_raw else None

        self._cache: Optional[_TTLCache] = (
            _TTLCache(max_items=max_items, ttl_sec=ttl_hours * 3600, persist_dir=persist_dir)
            if enabled
            else None
        )																# 💾 Перекладний кеш
        logger.info(
            "✅ AITaskService ініціалізовано",
            extra={
                "cache_enabled": enabled,
                "cache_ttl_hours": ttl_hours,
                "cache_max_items": max_items,
            },
        )

    # ================================
    # 🛠️ ДОПОМІЖНІ МЕТОДИ
    # ================================
    @staticmethod
    def _normalize_text_for_key(text: str) -> str:
        """🧽 Нормалізує текст, щоб стабільно формувати ключ кешу."""
        lowered = (text or "").strip().lower()                        # 🔡 Зводимо до нижнього регістру
        tokens = lowered.split()                                      # ✂️ Рубаємо повторні пробіли
        cleaned = " ".join(tokens)                                    # 🧽 Склеюємо назад одиночними пробілами
        return cleaned                                                # ↩️ Уніфікований рядок

    _CACHE_VERSION: str = "translation_v3"								# ♻️ Версія кешу (інвалідація старих записів)

    @classmethod
    def _make_key(cls, text: str) -> str:
        """🔑 Формує SHA-256 ключ від нормалізованого тексту."""
        normalized = cls._normalize_text_for_key(text)                 # ♻️ Нормалізуємо текст
        payload = f"{cls._CACHE_VERSION}:{normalized}".encode("utf-8")  # 🔠 Додаємо версію до ключа
        key = hashlib.sha256(payload).hexdigest()                      # 🔐 Генеруємо стабільний хеш
        logger.debug(
            "🔑 cache.key_built",
            extra={"normalized_len": len(normalized), "key_prefix": key[:8]},
        )                                                              # 🪵 Лог для діагностики
        return key                                                     # ↩️ Використовуємо як ключ кешу

    def _emit(self, name: str, payload: Dict[str, Any]) -> None:
        """📡 Безпечна обгортка для TelemetrySink."""
        try:
            self._telemetry.event(name, payload)
        except Exception as exc:										# noqa: BLE001
            logger.debug("⚠️ telemetry.emit_failed", extra={"event": name, "error": str(exc)})

    # ================================
    # ⚖️ ОЦІНКА ВАГИ
    # ================================
    async def estimate_weight_g(self, *, title: str, description: str, image_url: str) -> int:
        """⚖️ Оцінює вагу товару у грамах (fallback 1000 г)."""
        self._emit(
            "ai.weight.request",
            {"title_len": len(title or ""), "desc_len": len(description or ""), "has_image": bool(image_url)},
        )
        prompt = self._prompts.weight(title=title, description=description, image_url=image_url)  # ✏️ Створюємо промпт
        response = await self._openai.chat_completion(prompt)			# 🤖 Запит до OpenAI
        if not response:
            self._emit("ai.weight.result", {"ok": False, "reason": "empty"})
            logger.warning("⚖️ Відповідь ваги порожня — fallback 1000 г")
            return 1000
        try:
            kg = float(response.strip())								# 🔢 Парсимо результат
            grams = int(round(max(0.1, min(kg, 5.0)) * 1000))
            self._emit("ai.weight.result", {"ok": True, "grams": grams})
            logger.info("⚖️ Оцінена вага", extra={"grams": grams})
            return grams
        except ValueError:
            self._emit("ai.weight.result", {"ok": False, "reason": "parse_error"})
            logger.error("⚖️ Неможливо розпізнати вагу: %r — fallback 1000 г", response)
            return 1000

    # ================================
    # 🌐 ПЕРЕКЛАД І КЕШ
    # ================================
    async def translate_sections(self, *, text: str) -> Dict[str, str]:
        """🌐 Перекладає секції товару з кешуванням результату."""
        if not text:
            self._emit("ai.translate.request", {"text_len": 0, "empty": True})  # 🛰️ Телеметрія про пусте звернення
            logger.warning("🌐 Переклад: отримано порожній текст")       # ⚠️ Лог попередження
            return {}

        normalized_len = len(self._normalize_text_for_key(text))        # 📏 Контроль довжини нормалізованого тексту
        self._emit(
            "ai.translate.request",
            {"text_len": len(text), "norm_len": normalized_len},        # 🛰️ Перша телеметрія (до кешу)
        )

        cache_key = self._make_key(text)                                # 🔐 Детермінований ключ для кешу
        if self._cache:                                                 # 💾 Кеш може бути вимкнений у конфізі
            cached = self._cache.get(cache_key)                         # 🔍 Пробуємо витягти кешовані секції
            if cached is not None:
                self._emit("ai.translate.cache", {"hit": True, "sections": len(cached)})  # 🛰️ Хіт cache
                logger.debug("🌐 Translator cache HIT", extra={"sections": len(cached)})   # ✅ Лог для дебагу
                return cached                                           # ↩️ Повертаємо кеш/уникаємо OpenAI
            self._emit("ai.translate.cache", {"hit": False})            # 🛰️ Нема в кеші → збираємо з нуля

        prompt = self._prompts.translation(text=text)					# ✏️ Будуємо промпт
        response = await self._openai.chat_completion(prompt)			# 🤖 OpenAI
        if not response:
            self._emit("ai.translate.result", {"ok": False, "reason": "empty"})
            logger.warning("🌐 Переклад: відповідь порожня")
            return {}

        sections = {													# 📋 Базові секції, які очікуємо
            "МАТЕРІАЛ": "",
            "ПОСАДКА": "",
            "ОПИС": "",
            "МОДЕЛЬ": "",
        }
        current: Optional[str] = None									# 🧭 Поточна секція, у яку записуємо текст
        for raw_line in response.splitlines():							# 🔁 Проходимо рядки відповіді
            line = raw_line.strip()
            if not line:
                continue

            # 🔍 Пошук заголовка секції у форматі "<ключ>: ..."
            head, sep, tail = line.partition(":")
            if sep:													# ✂️ Маємо префікс із "ключ:"
                normalized_head = self._normalize_section_head(head)
                if normalized_head in sections:
                    current = normalized_head							# 📌 Запам'ятовуємо актуальну секцію
                    line = tail.strip()

            if current and line:										# 🧵 Додаємо контент до секції
                sections[current] += (line + " ")						# ✍️ Накопичуємо текст
        result = {
            key: value.strip()
            for key, value in sections.items()
            if value.strip()
        }																# 🧽 Фінальна очистка

        self._emit(
            "ai.translate.result",
            {"ok": True, "sections": len(result), "total_len": sum(len(value) for value in result.values())},
        )
        logger.info("🌐 Переклад виконано", extra={"sections": len(result)})

        if self._cache:
            self._cache.set(cache_key, result)
        return result

    @staticmethod
    def _normalize_section_head(head: str) -> str:
        """🔤 Прибирає емодзі/маркери з початку заголовка секції."""
        if not head:
            return ""
        cleaned = head.strip()
        cleaned = re.sub(r"^[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ]+", "", cleaned)	# 🚿 Очищаємо емодзі/маркери
        return cleaned.strip().upper()

    # ================================
    # ✨ СЛОГАН
    # ================================
    async def generate_slogan(self, *, title: str, description: str) -> str:
        """✨ Генерує короткий слоган (до 10 слів) або повертає fallback."""
        self._emit(
            "ai.slogan.request",
            {"title_len": len(title or ""), "desc_len": len(description or "")},
        )
        prompt = self._prompts.slogan(title=title, description=description)  # ✏️ Готуємо промпт
        response = await self._openai.chat_completion(prompt)				 # 🤖 OpenAI
        if not response:
            self._emit("ai.slogan.result", {"ok": False, "reason": "empty", "fallback": True})
            logger.warning("✨ Слоган: порожня відповідь — повертаємо дефолт")
            return DEFAULT_SLOGAN

        sanitized = response.replace('"', "").replace("'", "")			# 🧽 Прибираємо лапки
        words = sanitized.split()										# 🔠 Розбиваємо на слова
        cleaned = " ".join(words[:10])									# ✂️ Обмежуємо довжину
        self._emit("ai.slogan.result", {"ok": True, "len": len(cleaned)})
        logger.info("✨ Слоган згенеровано", extra={"len": len(cleaned)})
        return cleaned

    async def generate_banner_post(
        self,
        *,
        collection_label: str,
        product_names: Sequence[str],
        vibe_hint: str,
        link_count: int,
    ) -> str:
        """🪧 Формує Instagram-стиль caption на базі банера."""
        normalized_names = [name.strip() for name in product_names if name and name.strip()]
        self._emit(
            "ai.banner_post.request",
            {
                "label_len": len(collection_label or ""),
                "product_count": len(normalized_names),
                "link_count": link_count,
                "has_hint": bool(vibe_hint),
            },
        )
        product_blob = "\n".join(f"- {name}" for name in normalized_names) or "- YoungLA essentials"
        prompt = self._prompts.banner_post(
            collection_label=collection_label or "YoungLA drop",
            product_list=product_blob,
            vibe_hint=vibe_hint or "",
            link_count=max(0, link_count),
        )
        response = await self._openai.chat_completion(prompt)
        if not response:
            self._emit("ai.banner_post.result", {"ok": False, "reason": "empty", "fallback": True})
            logger.warning("🪧 Banner post: порожня відповідь — повертаємо fallback.")
            return DEFAULT_BANNER_POST

        cleaned = response.strip()
        self._emit("ai.banner_post.result", {"ok": True, "len": len(cleaned)})
        logger.info("🪧 Banner post згенеровано", extra={"len": len(cleaned)})
        return cleaned or DEFAULT_BANNER_POST


__all__ = ["AITaskService"]											# 📦 Публічний сервіс
