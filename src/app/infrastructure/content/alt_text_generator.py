# 🖼️ app/infrastructure/content/alt_text_generator.py
"""
🖼️ Генерує alt-тексти для зображень продуктів через OpenAI.

🔹 Підтримує кешування результатів у `HtmlLruCache`, щоб не дублювати запити.  
🔹 Використовує українські промпти та додає метрики (успіхи, збої, кеш-хіти).  
🔹 Працює з `ProductInfo`, повертаючи `{image_url: alt_text}` у порядку вхідних URL.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import asyncio															# 🔁 Обмеження конкурентних викликів
import hashlib															# 🧮 Формування ключів кешу
import json															# 📄 Парсинг відповіді LLM
import logging															# 🧾 Логування процесу
from typing import Dict, Iterable, List, Optional						# 📐 Типізація публічного API

# 🧩 Внутрішні модулі проєкту
from app.domain.products.entities import ProductInfo					# 📦 Дані продукту
from app.infrastructure.ai.dto import ChatMessage, ChatPrompt, Role		# 💬 DTO для LLM
from app.infrastructure.ai.open_ai_serv import OpenAIService			# 🤖 Обгортка OpenAI
from app.infrastructure.ai.prompt_service import PromptService			# 📝 Завантаження промптів
from app.shared.cache.html_lru_cache import HtmlLruCache				# 🧠 Кеш для alt-текстів
from app.shared.metrics.content import ALT_CACHE_HIT, ALT_FAILURE, ALT_SUCCESS	# 📊 Метрики контенту
from app.shared.utils.logger import LOG_NAME							# 🏷️ Назва логера

logger = logging.getLogger(LOG_NAME)									# 🧾 Модульний логер alt-генератора


# ================================
# 🧰 ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _norm_url(url: str) -> str:
    """
    🧰 Нормалізує URL (прибирає фрагмент `#...` і зайві пробіли).
    """
    cleaned = (url or "").strip()										# 🧼 Прибираємо пробіли
    normalized = cleaned.split("#", 1)[0]								# ✂️ Відкидаємо фрагмент
    return normalized


def _key_for(url: str) -> str:
    """
    🧰 Формує ключ кешу на основі sha256 нормалізованого URL.
    """
    hash_hex = hashlib.sha256(_norm_url(url).encode("utf-8")).hexdigest()	# 🔐 Стабільний ідентифікатор
    cache_key = f"alt:{hash_hex}"										# 🏷️ Простір імен alt-текстів
    return cache_key


# ================================
# 🖼️ ALT TEXT GENERATOR
# ================================
class AltTextGenerator:
    """
    🖼️ Генерує alt-тексти для переліку зображень продукту.

    Результат: `Dict[str, str]` — мапа URL → alt-текст.
    """

    def __init__(
        self,
        openai_service: OpenAIService,
        prompt_service: PromptService,
        *,
        cache: Optional[HtmlLruCache] = None,
        max_concurrency: int = 2,
    ) -> None:
        self._ai = openai_service										# 🤖 Обгортка OpenAI
        self._prompts = prompt_service									# 📝 Сервіс промптів
        self._cache = cache												# 🧠 Кеш alt-текстів
        self._sem = asyncio.Semaphore(max(1, int(max_concurrency)))		# 🚦 Ліміт паралельних викликів

    async def generate(self, product: ProductInfo, images: Iterable[str]) -> Dict[str, str]:
        """
        🖨️ Генерує alt-текст для кожного URL з `images`.
        """
        imgs: List[str] = [url for url in images if url]				# 🗂️ Фільтруємо порожні URL
        logger.info("🖼️ AltTextGenerator start: product=%s, images=%d", product.title, len(imgs))
        if not imgs:
            logger.debug("ℹ️ AltTextGenerator: список зображень порожній.")
            return {}

        hits: Dict[str, str] = {}										# ♻️ Кеш-хіти
        misses: List[str] = []											# 🚫 Що треба згенерувати
        if self._cache:
            for url in imgs:
                try:
                    cached_alt = await self._cache.get(_key_for(url))	# 🔐 Перевіряємо кеш
                except Exception:
                    cached_alt = None									# 🚫 Помилка кешу — ігноруємо
                if cached_alt:
                    hits[url] = cached_alt								# ✅ Хіт кешу
                else:
                    misses.append(url)									# 🟥 Міс
            if hits:
                try:
                    ALT_CACHE_HIT.labels(source="memory").inc(len(hits))	# 📊 Метрика кешу
                except Exception:
                    logger.debug("⚠️ ALT_CACHE_HIT метрика недоступна.")
                logger.debug("♻️ AltTextGenerator: кеш-хіти=%d, місси=%d", len(hits), len(misses))
        else:
            misses = imgs												# 💾 Кеш відсутній — все генеруємо
            logger.debug("ℹ️ AltTextGenerator: кеш не налаштований, працюємо без нього.")

        if not misses:
            logger.info("✅ AltTextGenerator: усі alt-тексти отримані з кешу.")
            return hits

        template = self._prompts.raw_prompt("alt_text.txt", lang="uk")	# 📝 Беремо український промпт
        sections = getattr(product, "sections", {}) or {}				# 📚 Додаткові секції продукту
        features = ", ".join(sorted(set(sections.keys())))				# 🧷 Інформація про секції

        prompt = template.format(										# ✍️ Заповнюємо плейсхолдери
            title=product.title or "",
            description=(product.description or "")[:400],
            features=features or "—",
        )
        prompt += f"\n\nЗгенеруй рівно {len(misses)} alt-текст(и) у форматі JSON-масиву рядків."
        logger.debug("📝 AltTextGenerator промпт готовий (зображень=%d).", len(misses))

        async with self._sem:											# 🚦 Троттлінг LLM
            try:
                chat_prompt = ChatPrompt(
                    messages=[ChatMessage(role=Role.USER, content=prompt)],
                    temperature=0.4,
                    max_tokens=400,
                )														# 📮 Підготовка запиту до LLM
                logger.info("🤖 Виклик OpenAI для %d зображень…", len(misses))
                text = await self._ai.chat_completion(chat_prompt)		# 📨 LLM-відповідь
                if text is None:
                    raise ValueError("empty_response")
            except Exception:
                try:
                    ALT_FAILURE.labels(source="ai", reason="exception").inc()
                except Exception:
                    logger.debug("⚠️ ALT_FAILURE метрика недоступна.")
                logger.exception("❌ AltTextGenerator: помилка під час виклику OpenAI.")
                raise

        items: List[str] = []											# 📋 Alt-тексти з відповіді
        try:
            data = json.loads(text)									# 📄 Пробуємо JSON
            if isinstance(data, list):
                items = [str(entry).strip() for entry in data]			# 🧼 Нормалізуємо рядки
            else:
                raise ValueError("not_list")
            logger.debug("📄 AltTextGenerator: LLM повернув JSON-масив довжиною %d.", len(items))
        except Exception:
            items = [line.strip("-• ").strip() for line in text.splitlines() if line.strip()]	# 🛟 Фолбек
            if not items:
                try:
                    ALT_FAILURE.labels(source="ai", reason="llm_parse").inc()
                except Exception:
                    logger.debug("⚠️ ALT_FAILURE метрика недоступна для llm_parse.")
                logger.error("❌ AltTextGenerator: не вдалося розпарсити відповідь LLM.")

        if len(items) < len(misses):
            filler = len(misses) - len(items)							# ➕ Скільки потрібно добити
            items += ["Фото товару"] * filler							# 🧩 Додаємо заглушки
            logger.debug("ℹ️ AltTextGenerator: добито %d заглушок.", filler)
        if len(items) > len(misses):
            items = items[: len(misses)]								# ✂️ Обрізаємо зайве

        generated = {url: alt for url, alt in zip(misses, items)}		# 🗂️ Мапа нових alt-текстів
        logger.info("🖋️ AltTextGenerator: згенеровано %d alt-текстів.", len(generated))

        if self._cache:
            for url, alt in generated.items():
                try:
                    await self._cache.set(_key_for(url), alt)			# 💾 Кладемо в кеш
                except Exception:
                    logger.debug("⚠️ AltTextGenerator: не вдалося записати у кеш для %s.", url)

        try:
            ALT_SUCCESS.labels(source="ai").inc(len(generated))		# 📊 Фіксуємо успіх
        except Exception:
            logger.debug("⚠️ ALT_SUCCESS метрика недоступна.")

        hits.update(generated)											# 🔗 Обʼєднуємо кеш-хіти та свіжі значення
        ordered = {url: hits[url] for url in imgs if url in hits}		# 📦 Повертаємо в початковому порядку
        logger.info("✅ AltTextGenerator завершився: повернуто %d alt-текстів.", len(ordered))
        return ordered
