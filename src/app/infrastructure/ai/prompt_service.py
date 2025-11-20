# 📬 app/infrastructure/ai/prompt_service.py
"""
📬 Інфраструктурний обгортка над shared PromptService.

🔹 Формує `ChatPrompt` (DTO) для OpenAIService із потрібними системними повідомленнями.
🔹 Підтягує `temperature` / `max_tokens` з конфіга з урахуванням overrides на промпт.
🔹 Уніфікує мову відповіді моделі: явний аргумент → конфіг → дефолт `uk`.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (зовнішніх залежностей немає)											# 🚫 Все на stdlib

# 🔠 Системні імпорти
import logging															# 🧾 Логування роботи сервісу
from typing import Any, Optional, Tuple								# 📐 Статична типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService					# ⚙️ Доступ до конфігів
from app.domain.ai.interfaces.prompt_service_interface import (		# 🧠 Контракт IPromptService
    Lang,
    ProductPromptDTO,
    Tone,
)
from app.shared.utils.locale import normalize_locale					# 🌍 Нормалізація локалі
from app.shared.utils.logger import LOG_NAME							# 🏷️ Базовий логер
from app.shared.utils.prompt_service import (							# ✏️ Загальний білдер текстів
    PromptService as SharedPromptBuilder,
    PromptType,
    ChartType,
)
from .dto import ChatPrompt, ChatMessage, Role							# 💬 DTO для AI-викликів


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai.prompts")					# 🧾 Виділений логер сервісу


# ================================
# 🧠 СЕРВІС ФОРМУВАННЯ ПРОМПТІВ
# ================================
class PromptService:
    """
    🧠 Будує `ChatPrompt` для різних сценаріїв (музика, слогани, переклади тощо),
    додаючи системне повідомлення про мову та конфігурований температурний профіль.
    """

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        cfg: ConfigService,
        builder: Optional[SharedPromptBuilder] = None,
        default_lang: Optional[str] = None,
    ) -> None:
        self._cfg = cfg													# ⚙️ Джерело параметрів
        self._builder = builder or SharedPromptBuilder()				# 🧱 Використовуємо спільний білдер
        cfg_lang = self._cfg.get("default_language", "uk", str) or "uk"	# 🌍 Мова з конфіга
        resolved_lang = normalize_locale(default_lang or cfg_lang, default=cfg_lang)  # 🧭 Остаточний код мови
        self._lang = resolved_lang										# 🌐 Зберігаємо дефолт для промптів
        logger.info(
            "🧠 prompt_service.init",
            extra={
                "lang": self._lang,
                "has_custom_builder": builder is not None,
            },
        )																# 🪵 Фіксуємо параметри запуску

    # ================================
    # 🛠️ ДОПОМІЖНІ ФУНКЦІЇ
    # ================================
    def _tt(self, key: str) -> Tuple[float, int]:
        """🌡️ Повертає (temperature, max_tokens) з урахуванням overrides."""
        defaults = self._cfg.get("openai.defaults", {}) or {}			# ⚙️ Загальні дефолти
        overrides = self._cfg.get(f"openai.prompts.{key}", {}) or {}	# 🧩 Пер- промптові значення
        temperature = float(overrides.get("temperature", defaults.get("temperature", 0.3)))  # 🌡️ Обране значення
        max_tokens = int(overrides.get("max_tokens", defaults.get("max_tokens", 1024)))  # 🧮 Ліміт токенів
        logger.debug(
            "🌡️ prompt_service.tt",
            extra={"prompt": key, "temperature": temperature, "max_tokens": max_tokens},
        )																# 🪵 Діагностичний запис
        return temperature, max_tokens									# ↩️ Віддаємо пару налаштувань

    def _lang_system_msg(self, lang_code: Optional[str] = None) -> Optional[ChatMessage]:
        """🌍 Мʼяка підказка моделі, якою мовою відповідати."""
        lang = (lang_code or self._lang) or "uk"						# 🌐 Визначаємо кінцеву мову
        text = {
            "uk": "Відповідай українською.",
            "ru": "Отвечай по-русски.",
            "en": "Reply in English.",
        }.get(lang)														# 💬 Текст системного повідомлення
        message = ChatMessage(Role.SYSTEM, text) if text else None		# 🧾 Створюємо ChatMessage
        logger.debug(
            "🌍 prompt_service.lang_system_msg",
            extra={"lang": lang, "has_message": message is not None},
        )																# 🪵 Пояснюємо рішення
        return message													# ↩️ Може бути None

    @staticmethod
    def _translation_hint(lang_code: Optional[str]) -> str:
        """💡 Додає hint до user-промпту, якщо білдер не підтримує target-lang."""
        lang = lang_code or "uk"										# 🌐 Цільова мова
        hint = {
            "uk": "Переклади та структуруй українською.",
            "ru": "Переведи и структурируй по-русски.",
            "en": "Translate and structure in English.",
        }.get(lang, "")													# 💡 Текст підказки
        return hint														# ↩️ Може бути порожнім рядком

    def _build_prompt(self, *, prompt_type: PromptType, system_lang: Optional[str], **builder_kwargs: Any) -> ChatPrompt:
        """🧱 Узагальнений конструктор ChatPrompt із логуванням."""
        prompt_text = self._builder.get_prompt(prompt_type, **builder_kwargs)  # ✏️ Генеруємо текст
        temperature, max_tokens = self._tt(prompt_type.value)			# 🌡️ Отримуємо налаштування
        system_message = self._lang_system_msg(system_lang)				# 🌍 Готуємо system-msg
        messages = ([system_message] if system_message else []) + [ChatMessage(Role.USER, prompt_text)]  # 📨 Формуємо чергу
        logger.info(
            "✏️ prompt_service.prompt_built",
            extra={
                "type": prompt_type.value,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "with_system_msg": system_message is not None,
            },
        )																# 🪵 Репортуємо готовий промпт
        return ChatPrompt(messages=messages, temperature=temperature, max_tokens=max_tokens)  # 📦 DTO для AI

    # ================================
    # 🎨 ПУБЛІЧНИЙ API (DTO)
    # ================================
    def slogan(self, *, title: str, description: str) -> ChatPrompt:
        """🎯 Повертає промпт для генерації слогану."""
        return self._build_prompt(
            prompt_type=PromptType.SLOGAN,
            system_lang=None,
            title=title,
            description=description,
        )																# ↩️ DTO для OpenAIService

    def banner_post(
        self,
        *,
        collection_label: str,
        product_list: str,
        vibe_hint: Optional[str],
        link_count: int,
    ) -> ChatPrompt:
        """🪧 Промпт для Instagram-поста за банером головної сторінки."""
        return self._build_prompt(
            prompt_type=PromptType.BANNER_POST,
            system_lang=None,
            collection_label=collection_label,
            product_list=product_list,
            vibe_hint=vibe_hint or "",
            link_count=link_count,
        )

    def music(self, *, title: str, description: str, image_url: str) -> ChatPrompt:
        """🎵 Опис композиції на основі даних товару."""
        return self._build_prompt(
            prompt_type=PromptType.MUSIC,
            system_lang=None,
            title=title,
            description=description,
            image_url=image_url,
        )

    def translation(self, *, text: str, target_lang: Optional[str] = None) -> ChatPrompt:
        """🌐 Промпт для перекладу з підказкою щодо цільової мови."""
        lang_code = target_lang or self._lang							# 🌍 Визначаємо мову перекладу
        lang_hint = self._translation_hint(lang_code)					# 💡 Пояснення для моделі
        composed_text = f"{lang_hint}\n\n{text}" if lang_hint else text	# 🧵 Додаємо hint до тіла
        return self._build_prompt(
            prompt_type=PromptType.TRANSLATION,
            system_lang=lang_code,
            text=composed_text,
        )

    def weight(self, *, title: str, description: str, image_url: str) -> ChatPrompt:
        """⚖️ Оцінка ваги товару за текстом та зображенням."""
        return self._build_prompt(
            prompt_type=PromptType.WEIGHT,
            system_lang=None,
            title=title,												# 🏷️ Назва товару
            description=description,									# 📄 Деталі для контексту
            image_url=image_url,										# 🖼️ Фото для аналізу
        )

    def clothing_type(self, *, title: str) -> ChatPrompt:
        """👕 Визначає категорію одягу."""
        return self._build_prompt(
            prompt_type=PromptType.CLOTHING_TYPE,
            system_lang=None,
            title=title,												# 🏷️ Єдиний аргумент для класифікації
        )

    def hashtags(self, *, title: str, description: str) -> ChatPrompt:
        """#️⃣ Генерує релевантні хештеги."""
        return self._build_prompt(
            prompt_type=PromptType.HASHTAGS,
            system_lang=None,
            title=title,												# 🏷️ Ключова назва
            description=description,									# 📄 Опис для кращого контексту
        )

    def size_chart(self, *, chart_type: ChartType) -> ChatPrompt:
        """📏 Формує загальний запит на побудову таблиці розмірів."""
        prompt_text = self._builder.get_size_chart_prompt(chart_type)	# 📊 Використовуємо спеціальний білдер
        temperature, max_tokens = self._tt("size_chart")				# 🌡️ Беремо налаштування
        system_message = self._lang_system_msg()						# 🌍 Мова відповіді
        messages = ([system_message] if system_message else []) + [ChatMessage(Role.USER, prompt_text)]  # 📨 Пакуємо повідомлення
        logger.info(
            "📏 prompt_service.size_chart",
            extra={"chart_type": chart_type.value, "with_system_msg": system_message is not None},
        )																# 🪵 Лог успішного складання
        return ChatPrompt(messages=messages, temperature=temperature, max_tokens=max_tokens)  # 📦 DTO

    def raw_prompt(self, fname: str, *, lang: Optional[str] = None) -> str:
        """📄 Повертає сирий шаблон (наприклад, для alt-text)."""
        target_lang = lang or self._lang								# 🌍 Якою мовою шукати шаблон
        text = self._builder.load_text(fname, lang=target_lang)		# 📄 Зчитуємо файл
        logger.debug(
            "📄 prompt_service.raw_prompt",
            extra={"fname": fname, "lang": target_lang, "has_text": bool(text)},
        )																# 🪵 Репорт
        return text														# ↩️ Повертаємо шаблон

    # ================================
    # 🤝 IPromptService-СУМІСНІСТЬ
    # ================================
    def get_music_prompt(self, product: ProductPromptDTO) -> ChatPrompt:
        """🎵 Сумісний метод IPromptService для музичних описів."""
        return self.music(
            title=product.title,										# 🏷️ Використовуємо назву товару
            description=product.description,							# 📄 Опис товару
            image_url=product.image_url or "",							# 🖼️ Посилання на зображення (fallback порожній)
        )

    def get_weight_prompt(self, product: ProductPromptDTO) -> ChatPrompt:
        """⚖️ Сумісний метод для ваги товару."""
        return self.weight(
            title=product.title,										# 🏷️ Назва для контексту
            description=product.description,							# 📄 Деталі для оцінки ваги
            image_url=product.image_url or "",							# 🖼️ Фото (якщо немає — порожній рядок)
        )

    def get_slogan_prompt(self, product: ProductPromptDTO, tone: Tone = Tone.SALES) -> ChatPrompt:
        """🎯 IPromptService API для слоганів (tone зберігаємо для forward-сумісності)."""
        logger.debug(
            "🎯 prompt_service.get_slogan_prompt",
            extra={"tone": tone.value},
        )																# 🪵 Відслідковуємо tone для дебагу
        return self.slogan(
            title=product.title,										# 🏷️ Вхідні дані для білдера
            description=product.description,							# 📄 Опис товару
        )

    def get_hashtags_prompt(self, product: ProductPromptDTO, lang: Lang = Lang.UK) -> ChatPrompt:
        """#️⃣ IPromptService API для хештегів (lang керується через дефолт)."""
        logger.debug(
            "#️⃣ prompt_service.get_hashtags_prompt",
            extra={"lang": lang.value},
        )																# 🪵 Фіксуємо запитану мову
        return self.hashtags(
            title=product.title,										# 🏷️ Назва товару
            description=product.description,							# 📄 Опис для генерації тегів
        )

    def get_translation_prompt(self, text: str, target_lang: Lang = Lang.UK) -> ChatPrompt:
        """🌐 IPromptService API для перекладу."""
        lang_code = target_lang.value if isinstance(target_lang, Lang) else str(target_lang)  # 🌍 Перетворюємо enum
        return self.translation(text=text, target_lang=lang_code)


__all__ = ["PromptService"]											# 📦 Експортований клас
