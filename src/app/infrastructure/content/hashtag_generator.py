# 🏷️ app/infrastructure/content/hashtag_generator.py
"""
🏷️ hashtag_generator.py — генерація хештегів для товарів YoungLA.
"""

# 🔠 Системні імпорти
import re                                                        # 🔤 Регулярні вирази для парсингу
import logging                                                   # 🧾 Логування
import asyncio                                                   # 🔄 Асинхронність
from typing import List, Set                                     # 🧰 Типи

# 🧩 Внутрішні модулі
from app.config.config_service import ConfigService              # ⚙️ Доступ до конфігурації
from app.infrastructure.ai.open_ai_serv import OpenAIService     # 🤖 GPT-сервіс
from app.infrastructure.ai.prompt_service import PromptService   # 💬 Генерація промптів
from app.shared.utils.logger import LOG_NAME                     # 📁 Назва логгера
from .gender_classifier import GenderClassifier                  # 🧬 Класифікатор статі товару

logger = logging.getLogger(LOG_NAME)


# ================================
# 🏛️ КЛАС ГЕНЕРАТОРА ХЕШТЕГІВ
# ================================
class HashtagGenerator:
    """
    🏷️ Генерує релевантні хештеги для товару на основі:
    - базових тегів із конфігурації
    - AI-доповнення через OpenAI
    - класифікації типу одягу та гендеру
    """

    def __init__(
        self,
        config_service: ConfigService,
        openai_service: OpenAIService,
        prompt_service: PromptService,
        gender_classifier: GenderClassifier,
    ):
        self.config = config_service									# ⚙️ Конфігурація (base hashtags)
        self.openai_service = openai_service								# 🤖 GPT-сервіс для генерації тегів
        self.prompt_service = prompt_service								# 💬 Побудова запитів для OpenAI
        self.gender_classifier = gender_classifier							# 🧬 Визначення гендеру товару

        self.base_hashtags: List[str] = self.config.get("hashtags.base", [])			# 🏷️ Базові хештеги з конфіга

    async def generate(self, title: str, description: str) -> str:
        """
        🧠 Генерує фінальний рядок унікальних валідних хештегів.

        Args:
            title (str): Назва товару
            description (str): Опис товару

        Returns:
            str: Відформатований рядок з хештегами
        """
        logging.info(f"🔍 Генерація хештегів для товару: {title}")

        hashtags = set(self.base_hashtags)								# 📥 Додаємо базові з конфіга

        article = self._extract_article(title)							# 🔎 Витягуємо артикул (W360, 4122...)
        hashtags.update(self.gender_classifier.classify(article))				# 🧬 Гендерні хештеги

        clothing_task = self._extract_clothing_type(title)						# 👕 Тип одягу
        ai_tags_task = self._generate_ai_hashtags(title, description)				# 🤖 Хештеги через GPT

        clothing_type, ai_hashtags = await asyncio.gather(clothing_task, ai_tags_task)

        if clothing_type:
            hashtags.add(f"#{clothing_type.replace(' ', '').lower()}")				# 🧵 Тип одягу як тег

        hashtags.update(ai_hashtags)								# ➕ AI-теги в сет

        sanitized_hashtags = {
            self._sanitize_hashtag(h) for h in hashtags if self._sanitize_hashtag(h)
        }                                                       # 🧹 Очищаємо хештеги (тільки букви/цифри)

        return " ".join(sorted(list(sanitized_hashtags)))					# 📦 Результат: рядок тегів через пробіл

    def _extract_article(self, title: str) -> str:
        """
        🔎 Витягує артикул з назви (наприклад, 'W360' → 'W360').
        """
        match = re.match(r"^([A-Za-z0-9]+)", title)
        return match.group(1) if match else ""

    async def _extract_clothing_type(self, title: str) -> str:
        """
        👕 Визначає тип одягу (tee, joggers, hoodie...) через AI.
        """
        prompt = self.prompt_service.get_clothing_type_prompt(title=title)
        response = await self.openai_service.chat_completion(prompt, temperature=0)
        return response.strip().lower() if response else ""

    async def _generate_ai_hashtags(self, title: str, description: str) -> Set[str]:
        """
        🤖 Генерує хештеги на основі GPT-відповіді.
        """
        prompt = self.prompt_service.get_hashtags_prompt(title=title, description=description)
        response = await self.openai_service.chat_completion(prompt, temperature=0.5)

        if not response:
            return set()

        return set(re.findall(r"#\w+", response))						# 🧠 Витягуємо всі слова через #

    def _sanitize_hashtag(self, hashtag: str) -> str:
        """
        🧹 Очищує хештег від невалідних символів.
        """
        clean_tag = re.sub(r"[^a-zA-Z0-9а-яА-ЯіІїЇєЄ_]", "", hashtag.replace("#", ""))
        if not clean_tag:
            return ""
        return f"#{clean_tag.lower()}"								# 🔠 Перетворення в нижній регістр + #