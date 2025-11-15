# ⚖️ app/domain/products/services/weight_resolver.py
"""
⚖️ `WeightResolver` — доменний сервіс визначення ваги товару у грамах.

🔹 Узгоджує локальні дані (WeightDataService) та AI-оцінювач (IWeightEstimator) через єдиний API.
🔹 Виконує послідовність fallback-ів із детальним DEBUG-логуванням і безпечними clamp-ами.
🔹 Дотримується IMP-027: відсутність побічних ефектів у __init__ та шанобливе поводження з asyncio.CancelledError.
"""

from __future__ import annotations                                                   # ⏳ Дозволяємо посилатися на типи, оголошені нижче

# 🔠 Системні імпорти
import asyncio                                                                       # 🔁 Асинхронні локи для майбутнього розширення
import logging                                                                       # 🧾 Єдине джерело логування
from dataclasses import dataclass                                                    # 🧱 Опис сервісу як dataclass
from typing import Optional, TYPE_CHECKING                                           # 🧰 Анотації та гейт для type-checker

# 🧩 Внутрішні модулі проєкту
try:
    from app.shared.utils.logger import LOG_NAME                                     # 🏷️ Глобальний префікс логерів застосунку
except Exception:  # pragma: no cover
    LOG_NAME = __name__                                                              # 🪪 Фолбек під час ізольованих тестів

try:
    from app.domain.ai.task_contracts import IWeightEstimator as _ImportedIWeightEstimator  # 🤖 Контракт AI-оцінки ваги
except Exception:  # pragma: no cover
    class _FallbackIWeightEstimator:  # type: ignore[too-few-public-methods]
        """Fallback-стаб для тестів без ai.task_contracts."""

        async def estimate_weight_g(self, *, title: str, description: str, image_url: str) -> int:
            raise NotImplementedError("AI estimator недоступний у цій збірці")        # 🚫 Чіткий сигнал про відсутність реалізації

    _ImportedIWeightEstimator = _FallbackIWeightEstimator                             # 🧊 Переходимо на стаб

try:
    from app.infrastructure.data_storage.weight_data_service import WeightDataService as _ImportedWeightDataService  # 💾 Джерело локальних хінтів
except Exception:  # pragma: no cover
    class _FallbackWeightDataService:  # type: ignore[too-few-public-methods]
        """Fallback-стаб для локальних тестів без інфра-шару."""

        def get_weight_hint(self, *, title: str, description: str) -> Optional[int]:
            logger = logging.getLogger(__name__)                                      # 🧾 Локальний логер для fallback-а
            logger.debug("💤 WeightDataService.stub: повертаємо None")                # 💤 Фіксуємо відсутність даних
            return None                                                               # 🧊 Немає даних у мінімальній збірці

    _ImportedWeightDataService = _FallbackWeightDataService                           # 🧊 Використовуємо стаб

if TYPE_CHECKING:
    from app.domain.ai.task_contracts import IWeightEstimator as WeightEstimatorType  # 🤖 Тип для статичної перевірки
    from app.infrastructure.data_storage.weight_data_service import WeightDataService as WeightDataServiceType  # 💾 Тип для статичної перевірки
else:
    WeightEstimatorType = _ImportedIWeightEstimator                                   # 🔁 Використовуємо доступний у рантаймі клас
    WeightDataServiceType = _ImportedWeightDataService                                # 🔁 Використовуємо доступний у рантаймі клас


# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
MODULE_LOGGER_NAME: str = f"{LOG_NAME}.domain.products.weight"                       # 🏷️ Конкретний суфікс для сервісу
logger = logging.getLogger(MODULE_LOGGER_NAME)                                       # 🧾 Ініціалізуємо модульний логер
logger.debug("⚖️ WeightResolver module import стартував")                           # 🚀 Діагностуємо завантаження модуля


# ================================
# ⚙️ САНІТІ-КОНСТАНТИ
# ================================
DEFAULT_WEIGHT_G: int = 0                                                            # 🧊 Повний fallback у грамах
MIN_WEIGHT_G: int = 0                                                                # 🔽 Мінімальна допустима вага
MAX_WEIGHT_G: int = 5_000                                                            # 🔼 Максимум (~5 кг) у межах домену
logger.debug(
    "⚙️ WeightResolver constants set | default=%s min=%s max=%s",
    DEFAULT_WEIGHT_G,
    MIN_WEIGHT_G,
    MAX_WEIGHT_G,
)                                                                                     # 🧾 Фіксуємо ініціалізацію меж


# ================================
# 🧮 ДОПОМІЖНА ФУНКЦІЯ
# ================================
def _clamp_weight_g(value: int) -> int:
    """
    Обмежує значення у [MIN_WEIGHT_G, MAX_WEIGHT_G], логуючи всі етапи.

    Args:
        value: Кандидат у грамах (може бути будь-який int-подібний об'єкт).

    Returns:
        Відкоригована вага у грамах, гарантовано в діапазоні.
    """
    logger.debug("🧮 _clamp_weight_g старт | raw=%r", value)                           # 🧾 Фіксуємо початкове значення
    try:
        converted: int = int(value)                                                   # 🔁 Пробуємо привести до int
        logger.debug("🧮 _clamp_weight_g int(%r) → %s", value, converted)             # 📐 Фіксуємо результат приведення
    except Exception:
        logger.debug(
            "⚠️ _clamp_weight_g: неможливо конвертувати %r → використовуємо %s г",
            value,
            DEFAULT_WEIGHT_G,
        )                                                                             # 🚨 Діагностуємо некоректне значення
        return DEFAULT_WEIGHT_G                                                       # 🧊 Повертаємо дефолт через помилку

    if converted < MIN_WEIGHT_G:
        logger.debug(
            "🔽 _clamp_weight_g: %s < %s → clamp до %s",
            converted,
            MIN_WEIGHT_G,
            MIN_WEIGHT_G,
        )                                                                             # 🔽 Фіксуємо занижену вагу
        return MIN_WEIGHT_G                                                           # 🔒 Віддаємо мінімум
    if converted > MAX_WEIGHT_G:
        logger.debug(
            "🔼 _clamp_weight_g: %s > %s → clamp до %s",
            converted,
            MAX_WEIGHT_G,
            MAX_WEIGHT_G,
        )                                                                             # 🔼 Фіксуємо завищену вагу
        return MAX_WEIGHT_G                                                           # 🔒 Віддаємо максимум

    logger.debug("✅ _clamp_weight_g: %s у межах → повертаємо без змін", converted)    # ✅ Значення коректне
    return converted                                                                  # 📤 Повертаємо нормалізоване значення


# ================================
# 🏛️ СЕРВІС ВИЗНАЧЕННЯ ВАГИ
# ================================
@dataclass(slots=True)
class WeightResolver:
    """
    Єдина точка отримання ваги товару (грами, `int`) з передбачуваною послідовністю fallback-ів.

    Порядок джерел:
        1️⃣ `WeightDataService` (локальна база) — миттєвий хінт.
        2️⃣ `IWeightEstimator` (AI) — лише якщо є валідний `image_url`.
        3️⃣ Дефолт (`DEFAULT_WEIGHT_G`).
    """

    weight_data_service: Optional[WeightDataServiceType] = None                      # 💾 DI: локальне джерело даних
    ai_estimator: Optional[WeightEstimatorType] = None                               # 🤖 DI: AI оцінювач
    _lock: asyncio.Lock = asyncio.Lock()                                             # 🔐 Майбутній захист від паралельного доступу

    # ================================
    # 📤 ПУБЛІЧНИЙ API
    # ================================
    async def resolve_g(self, title: str, description: str = "", image_url: Optional[str] = None) -> int:
        """
        Повертає вагу в грамах, використовуючи послідовність джерел і детальне логування.

        Args:
            title: Назва товару (обов'язкова).
            description: Опис товару (може бути порожнім).
            image_url: URL зображення (використовується лише для AI).

        Returns:
            int: Вага у грамах, обмежена clamp-ом.
        """
        logger.debug(
            "⚙️ resolve_g invoked | raw_title=%r raw_description_len=%d raw_image_url=%r",
            title,
            len(description or ""),
            image_url,
        )                                                                             # 🧾 Стартуємо діагностику виклику
        normalized_title: str = (title or "").strip()                                 # 🧼 Санітизуємо назву
        normalized_description: str = (description or "").strip()                     # 🧼 Санітизуємо опис
        normalized_image: str = (image_url or "").strip() if image_url else ""        # 🧼 Санітизуємо URL зображення
        logger.debug(
            "🧼 Sanitized fields | title_len=%d description_len=%d has_image=%s",
            len(normalized_title),
            len(normalized_description),
            bool(normalized_image),
        )                                                                             # 📊 Фіксуємо стан після препроцесингу

        hint: Optional[int] = await self._try_weight_data(normalized_title, normalized_description)  # 💾 Пробуємо локальний хінт
        if hint is not None:
            logger.debug("💾 weight_data_service → сирий хінт %s г", hint)             # 🧾 Знайдено значення у локальній базі
            clamped_hint: int = _clamp_weight_g(hint)                                  # 🔒 Нормалізуємо результат
            logger.debug("💾 weight_data_service → повертаємо %s г (clamped)", clamped_hint)  # ✅ Підтверджуємо фінал
            return clamped_hint                                                       # 📤 Видаємо вагу з локальної бази

        if not normalized_image:
            logger.debug("🧊 resolve_g: відсутній image_url → fallback до %s г", DEFAULT_WEIGHT_G)  # 🧾 Немає підстав для AI
            return DEFAULT_WEIGHT_G                                                    # 🧊 Видаємо дефолт

        if self.ai_estimator:
            logger.debug("🤖 resolve_g: запускаємо AI-оцінку")                         # 🚀 Старт AI
            try:
                estimation: int = await self.ai_estimator.estimate_weight_g(           # 🤖 Отримуємо прогноз ваги
                    title=normalized_title,
                    description=normalized_description,
                    image_url=normalized_image,
                )
                logger.debug("🤖 ai_estimator повернув %s г до clamp", estimation)    # 📊 Фіксуємо сирий результат
                clamped_ai: int = _clamp_weight_g(estimation)                         # 🔒 Стандартизуємо значення
                logger.debug("🤖 ai_estimator → повертаємо %s г (clamped)", clamped_ai)  # ✅ Посилюємо діагностику
                return clamped_ai                                                     # 📤 Віддаємо оцінку AI
            except asyncio.CancelledError:  # pragma: no cover
                logger.debug("🛑 resolve_g: отримали asyncio.CancelledError → проброс")  # 🛑 Поважаємо відміну
                raise                                                                  # 🔁 Не ховаємо сигнал скасування
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "🤖 resolve_g: AI виняток=%r → %s г",
                    exc,
                    DEFAULT_WEIGHT_G,
                    exc_info=True,
                )                                                                       # ⚠️ Фіксуємо причину падіння AI
                return DEFAULT_WEIGHT_G                                                 # 🧊 Фолбек на дефолт

        logger.debug("🧊 resolve_g: немає доступних джерел → %s г", DEFAULT_WEIGHT_G)   # 🧾 Жодне джерело не спрацювало
        return DEFAULT_WEIGHT_G                                                        # 🧊 Останній fallback

    # ================================
    # 🔒 ВНУТРІШНІ МЕТОДИ
    # ================================
    async def _try_weight_data(self, title: str, description: str) -> Optional[int]:
        """
        Пробує отримати вагу з локального сервісу `WeightDataService`.
        """
        logger.debug(
            "🔍 _try_weight_data старт | title_len=%d description_len=%d service=%s",
            len(title),
            len(description),
            bool(self.weight_data_service),
        )                                                                             # 🧾 Вхідні параметри
        service: Optional[WeightDataServiceType] = self.weight_data_service          # 💾 Кешуємо сервіс у локальну змінну
        if not service:
            logger.debug("ℹ️ _try_weight_data: weight_data_service відсутній")        # 💤 DI не передано
            return None                                                               # 🚫 Немає джерела → відразу None

        try:
            hint: Optional[int] = service.get_weight_hint(                            # type: ignore[attr-defined]
                title=title,
                description=description,
            )                                                                         # 💬 Питаємо локальну базу
            if hint is None:
                logger.debug("ℹ️ _try_weight_data: weight_data_service не знає вагу %r", title)  # 💤 База мовчить
                return None                                                           # 🚫 Продовжуємо до наступного джерела
            logger.debug("💾 _try_weight_data: weight_data_service знайшов %s г", hint)  # 🧾 Є значення
            clamped_hint: int = _clamp_weight_g(hint)                                  # 🔒 Стандартизуємо перед поверненням
            logger.debug("💾 _try_weight_data: clamp після weight_data_service → %s г", clamped_hint)  # ✅ Підтверджуємо clamp
            return clamped_hint                                                       # 📤 Повертаємо нормалізовану вагу
        except asyncio.CancelledError:  # pragma: no cover
            logger.debug("🛑 _try_weight_data: asyncio.CancelledError → проброс")      # 🛑 Поважаємо скасування
            raise                                                                      # 🔁 Перекидаємо далі
        except Exception as exc:  # noqa: BLE001
            logger.debug("⚠️ _try_weight_data: exception=%r → продовжуємо без локального сервісу", exc, exc_info=True)  # 🧯 Ігноруємо помилки
            return None                                                               # 🚫 Повертаємо None для наступних джерел


# ================================
# 🔓 ПУБЛІЧНИЙ API МОДУЛЯ
# ================================
__all__ = ["WeightResolver"]                                                          # 📤 Експортуємо основний сервіс
logger.debug("🔓 WeightResolver додано до __all__: %s", __all__)                      # 🧾 Підтверджуємо публічний API
