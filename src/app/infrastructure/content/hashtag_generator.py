# 🏷️ app/infrastructure/content/hashtag_generator.py
"""
🏷️ Інфраструктурна реалізація `IHashtagGenerator` для товарів YoungLA.

🔹 Генерує хештеги на основі базових конфігів, гендерних правил і підказок OpenAI.  
🔹 Повертає множину унікальних тегів без `#`-дублів чи сміття.  
🔹 Веде детальне логування всіх кроків, щоби спростити діагностику.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import asyncio                                                      # 🔁 Виклики OpenAI в паралелі
import logging                                                      # 🧾 Логи генерування
import re                                                           # 🔍 Витяг хештегів із тексту
from typing import Dict, List, Set                                  # 📐 Типи публічного API

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                 # ⚙️ Конфіги для базових тегів
from app.domain.content.interfaces import IHashtagGenerator         # 🤝 Доменний контракт
from app.domain.products.entities import ProductInfo                # 📦 Опис продукту
from app.infrastructure.ai.open_ai_serv import OpenAIService        # 🤖 Взаємодія з OpenAI
from app.infrastructure.ai.prompt_service import PromptService      # 📝 Промпти для генерації
from app.shared.utils.logger import LOG_NAME                        # 🏷️ Базове імʼя логера

logger = logging.getLogger(f"{LOG_NAME}.ai")                       # 🧾 Логер підсистеми AI


# ================================
# 🏷️ ГЕНЕРАТОР ХЕШТЕГІВ
# ================================
class HashtagGenerator(IHashtagGenerator):
    """🏷️ Повертає множину валідних хештегів для переданого `ProductInfo`."""

    def __init__(
        self,
        config_service: ConfigService,
        openai_service: OpenAIService,
        prompt_service: PromptService,
        gender_rules: Dict[str, List[str]],
    ) -> None:
        self.config = config_service                                 # ⚙️ Джерело базових тегів
        self.openai = openai_service                                 # 🤖 OpenAI клієнт
        self.prompts = prompt_service                                # 📝 Постачальник промптів
        self.gender_rules = gender_rules                             # 🚻 Префікс → хештеги

        raw_base: List[str] = self.config.get(
            "hashtags.base",
            [],
            cast=lambda v: [str(x) for x in v] if isinstance(v, (list, tuple, set)) else [],
        ) or []                                                      # 📦 Базовий список із конфіга
        self.base_hashtags: List[str] = [
            tag.strip()
            for tag in raw_base
            if isinstance(tag, str) and tag.strip()
        ]                                                            # 🧼 Чистимо та фільтруємо
        logger.debug("🏷️ Базові хештеги (%d): %s", len(self.base_hashtags), self.base_hashtags)

    async def generate(self, product: ProductInfo) -> Set[str]:
        """Генерує множину унікальних хештегів для товару."""
        title = product.title or ""                                 # 🏷️ Назва товару
        description = product.description or ""                     # 📝 Опис товару
        logger.info("🏷️ Старт генерації хештегів для: %s", title)

        tags: Set[str] = set(self.base_hashtags)                     # 📚 Починаємо з базових тегів

        article = self._extract_article(title)                       # 🔎 Витягуємо артикул
        tags.update(self._gender_tags(article))                      # 🚻 Додаємо гендерні теги
        logger.debug("🚻 Гендерні теги для %s: %s", article, tags)

        clothing_task = self._extract_clothing_type(title)           # 👕 Тип одягу (AI)
        ai_tags_task = self._generate_ai_hashtags(title, description)  # 🤖 Додаткові теги від LLM
        clothing_type, ai_tags = await asyncio.gather(clothing_task, ai_tags_task)
        logger.debug("👕 Тип одягу=%s, AI-теги=%s", clothing_type, ai_tags)

        if clothing_type:
            normalized_type = clothing_type.replace(" ", "").lower()  # 🧼 Видаляємо пробіли
            tags.add(f"#{normalized_type}")                           # ➕ Додаємо тег типу одягу

        tags.update(ai_tags)                                         # 🤖 Інтегруємо AI-теги
        sanitized = {
            sanitized_tag
            for tag in tags
            if (sanitized_tag := self._sanitize_hashtag(tag))
        }                                                            # 🧼 Санітуємо кожен тег
        logger.info("✅ Згенеровано %d валідних хештегів.", len(sanitized))
        return sanitized

    # ================================
    # 🔧 ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _extract_article(self, title: str) -> str:
        """Витягує префікс артикула (букви/цифри на початку)."""
        match = re.match(r"^([A-Za-z0-9]+)", title or "")          # 🧵 Перший блок літер/цифр із назви
        article = match.group(1) if match else ""                    # 🧾 Або порожній рядок, якщо не знайшли
        logger.debug("🔎 Артикул з назви '%s' → '%s'", title, article)
        return article

    def _gender_tags(self, article: str) -> List[str]:
        """Повертає гендерні теги за префіксом артикула."""
        for prefix, tags in self.gender_rules.items():
            if prefix == "default":                                  # 🛡️ Пропускаємо fallback на цьому кроці
                continue
            if article.startswith(prefix):
                logger.info("🚻 Вибрано гендерні теги '%s' → %s", prefix, tags)
                return tags
        fallback = self.gender_rules.get("default", [])              # 🛟 Fallback-набір хештегів
        logger.info("🚻 Використано fallback (default) теги: %s", fallback)
        return fallback

    async def _extract_clothing_type(self, title: str) -> str:
        """Викликає OpenAI для визначення типу одягу."""
        prompt = self.prompts.clothing_type(title=title)             # 📝 Формуємо промпт
        response = await self.openai.chat_completion(prompt)         # 🤖 Отримуємо відповідь
        if not response:
            logger.warning("⚠️ OpenAI clothing_type вернув порожній результат.")
            return ""
        clothing_type = response.strip().lower()                     # 🧼 Прибираємо пробіли, приводимо до lower
        logger.debug("👕 clothing_type='%s'", clothing_type)
        return clothing_type

    async def _generate_ai_hashtags(self, title: str, description: str) -> Set[str]:
        """Генерує AI-хештеги з врахуванням назви та опису товару."""
        prompt = self.prompts.hashtags(title=title, description=description)
        response = await self.openai.chat_completion(prompt)         # 📩 Відправляємо запит у LLM
        if not response:
            logger.warning("⚠️ OpenAI hashtags вернув порожній результат.")
            return set()
        found = set(re.findall(r"#\w+", response))                 # 🔍 Витягуємо всі #теги
        logger.debug("🤖 AI повернув %d тегів: %s", len(found), found)
        return found

    def _sanitize_hashtag(self, hashtag: str) -> str:
        """Санітує тег: прибирає зайві символи, повертає в нижньому регістрі."""
        cleaned = re.sub(r"[^a-zA-Z0-9а-яА-ЯіІїЇєЄ_]", "", (hashtag or "").replace("#", ""))
        sanitized = f"#{cleaned.lower()}" if cleaned else ""        # 🧼 Якщо лишилися символи — додаємо # і lower
        logger.debug("🧼 sanitize: %r → %r", hashtag, sanitized)
        return sanitized


__all__ = ["HashtagGenerator"]
