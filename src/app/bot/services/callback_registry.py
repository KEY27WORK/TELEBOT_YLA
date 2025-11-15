# 🗂️ app/bot/services/callback_registry.py
"""
🗂️ callback_registry.py — центральний реєстр для обробників inline‑кнопок.

🎯 Призначення:
    • Зберігає відповідності між ключем (CallbackData) і async‑обробником
    • Надає зручний API реєстрації/отримання/зняття обробників
    • Пише діагностичні логи (конфлікти, джерела реєстрації)

⚙️ Особливості реалізації:
    • Валідація ключів (тип CallbackData)
    • Перевірка, що обробники — корутини (async def)
    • Мʼяка перевірка сигнатури (2 параметри: Update, CustomContext) — попереджає, не падає
    • Утиліти: unregister(), clear(), items()/keys()/values(), register_map()
    • Сумісність з існуючим кодом (використовуємо .key у CallbackData)
"""

# 🔠 Системні імпорти
import inspect													# 🔎 Перевірка корутин і сигнатур
import logging													# 🧾 Логування
from typing import Dict, Iterable, ItemsView, KeysView, Optional, ValuesView	# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME							# 🏷️ Імʼя проєктного логера
from .types import CallbackHandlerType, Registrable					# 🧱 Протоколи/аліаси типів
from .callback_data_factory import CallbackData						# 🧩 Ключ callback‑даних

# (мʼяка перевірка анотацій сигнатури)
try:
    from telegram import Update										# 📦 Тип з telegram
    from .custom_context import CustomContext						# 🧩 Кастомний контекст бота
except Exception:  # pragma: no cover
    Update = object  # type: ignore
    CustomContext = object  # type: ignore


# ==========================
# 🧾 ЛОГЕР
# ==========================
logger = logging.getLogger(LOG_NAME)									# 🧭 Централізований логер

__all__ = ["CallbackRegistry"]


# ==========================
# 🏛️ РЕЄСТР CALLBACK-ОБРОБНИКІВ
# ==========================
class CallbackRegistry:
    """
    🗂️ Реєстр callback'ів: зберігає звʼязок між ключем `CallbackData` та async‑обробником.

    Використання:
        1) Фіча (feature) реалізує інтерфейс `Registrable` і надає `get_callback_handlers()`
        2) `CallbackRegistry.register(feature_instance)` реєструє всі пари (key → handler)
        3) `get_handler(key)` повертає обробник або `None`
    """

    # ==========================
    # ⚙️ ІНІЦІАЛІЗАЦІЯ
    # ==========================
    def __init__(self) -> None:
        """Створює порожній реєстр."""
        self._handlers: Dict[CallbackData, CallbackHandlerType] = {}			# 📦 Сховище пар key→handler

    # ==========================
    # ➕ РЕЄСТРАЦІЯ
    # ==========================
    def register(self, feature_instance: Registrable) -> None:
        """
        Реєструє всі обробники, що повертає `feature_instance.get_callback_handlers()`.

        Args:
            feature_instance: Екземпляр фічі, який надає словник обробників.

        Raises:
            TypeError: якщо ключ не `CallbackData` або обробник не async‑функція.
        """
        origin = feature_instance.__class__.__name__						# 🏷️ Джерело для логів
        for key, handler in feature_instance.get_callback_handlers().items():
            self._register_pair(key, handler, origin_hint=origin)				# 🔗 Делегація на внутрішню реєстрацію

    def register_map(self, mapping: Dict[CallbackData, CallbackHandlerType], *, origin: str = "manual") -> None:
        """
        Реєструє обробники з готового словника.

        Args:
            mapping: Словник {CallbackData: async‑handler}.
            origin: Текстове джерело реєстрації для логів.
        """
        for key, handler in mapping.items():
            self._register_pair(key, handler, origin_hint=origin)				# 📥 Масова реєстрація

    # ==========================
    # 🔍 ОТРИМАННЯ
    # ==========================
    def get_handler(self, key: CallbackData) -> Optional[CallbackHandlerType]:
        """
        Повертає обробник за ключем або `None`, якщо не знайдено.

        Args:
            key: Ключ callback‑даних.

        Returns:
            Обробник або None.
        """
        return self._handlers.get(key)										# 🔎 Пошук у словнику

    # ==========================
    # ➖ СНЯТТЯ / СКИДАННЯ
    # ==========================
    def unregister(self, key: CallbackData) -> None:
        """
        Видаляє обробник для вказаного ключа, якщо він існує.

        Args:
            key: Ключ, для якого потрібно зняти реєстрацію.
        """
        if key in self._handlers:
            self._handlers.pop(key, None)									# 🗑️ Видалення без KeyError
            logger.info("🗑️ Обробник для callback '%s' знятий з реєстрації.", key.key)

    def clear(self) -> None:
        """Повністю очищає реєстр (зручно для тестів/переініціалізації)."""
        count = len(self._handlers)										# 🔢 Скільки було зареєстровано
        self._handlers.clear()											# 🧹 Повний скидання
        logger.info("🧹 Реєстр callback‑обробників очищено (видалено %d).", count)

    # ==========================
    # 📚 ІТЕРАЦІЇ/ВИДИ
    # ==========================
    def items(self) -> ItemsView[CallbackData, CallbackHandlerType]:
        """Повертає items() для перебору (key, handler)."""
        return self._handlers.items()										# 🔁 Ітерація по парам

    def keys(self) -> KeysView[CallbackData]:
        """Повертає keys() для перебору ключів."""
        return self._handlers.keys()										# 🗝️ Перелік ключів

    def values(self) -> ValuesView[CallbackHandlerType]:
        """Повертає values() для перебору обробників."""
        return self._handlers.values()									# 🔧 Перелік обробників

    # ==========================
    # ℹ️ СЛУЖБОВЕ
    # ==========================
    def __len__(self) -> int:
        """Кількість зареєстрованих обробників."""
        return len(self._handlers)										# 🔢 Розмір реєстру

    def __contains__(self, key: CallbackData) -> bool:
        """Перевірка наявності ключа: `key in registry`."""
        return key in self._handlers										# ✅ True/False

    # ==========================
    # 🔒 ВНУТРІШНЯ РЕЄСТРАЦІЯ ПАРИ
    # ==========================
    def _register_pair(
        self,
        key: CallbackData,
        handler: CallbackHandlerType,
        *,
        origin_hint: str,
    ) -> None:
        """
        Реєструє одну пару (key → handler) з повними перевірками.

        Args:
            key: Екземпляр `CallbackData`.
            handler: Async‑обробник.
            origin_hint: Текст для логів — звідки прийшла реєстрація (імʼя фічі/«manual»).

        Raises:
            TypeError: якщо ключ не `CallbackData` або обробник не async‑функція.
        """
        # 1) Тип ключа
        if not isinstance(key, CallbackData):
            raise TypeError(f"Ключ для callback‑обробника має бути типу CallbackData, а не {type(key)}")

        # 2) Обробник — корутина?
        if not inspect.iscoroutinefunction(handler):
            raise TypeError(f"Обробник для '{key.key}' має бути async‑функцією (async def).")

        # 3) Мʼяка перевірка сигнатури (не падаємо, лише попереджаємо)
        self._warn_if_signature_suspicious(key, handler)

        # 4) Конфлікт ключів — попереджаємо, але перезаписуємо (очікувана поведінка)
        if key in self._handlers:
            logger.warning("⚠️ Обробник для '%s' перезаписано (джерело: %s).", key.key, origin_hint)

        self._handlers[key] = handler									# 💾 Зберігаємо пару в реєстрі
        logger.info("✅ Обробник для callback '%s' зареєстровано (джерело: %s).", key.key, origin_hint)

    # ==========================
    # 🧪 МʼЯКА ПЕРЕВІРКА СИГНАТУРИ
    # ==========================
    def _warn_if_signature_suspicious(self, key: CallbackData, handler: CallbackHandlerType) -> None:
        """
        Попереджає, якщо сигнатура обробника «підозріла».

        Потрібний контракт: (Update, CustomContext) -> Awaitable[None]
        Перевірка мʼяка: попередження в лог, без виключень.
        """
        try:
            sig = inspect.signature(handler)								# 📐 Зчитуємо сигнатуру
        except (TypeError, ValueError):  # pragma: no cover
            logger.warning("⚠️ Не вдалося прочитати сигнатуру обробника '%s'.", key.key)
            return

        params = list(sig.parameters.values())
        if len(params) != 2:
            logger.warning(
                "⚠️ Обробник '%s' має приймати рівно 2 параметри (Update, CustomContext). Зараз: %d.",
                key.key,
                len(params),
            )
            return

        p0, p1 = params[0], params[1]
        # Якщо анотацій немає — не сваримось, лише підказуємо при явних невідповідностях.
        if p0.annotation not in (inspect._empty, Update):
            logger.warning(
                "⚠️ Handler '%s': перший параметр не аннотований як 'Update' (annotation=%r).",
                key.key,
                p0.annotation,
            )
        if p1.annotation not in (inspect._empty, CustomContext):
            logger.warning(
                "⚠️ Handler '%s': другий параметр не аннотований як 'CustomContext' (annotation=%r).",
                key.key,
                p1.annotation,
            )

    # ==========================
    # 🧰 ДОДАТКОВЕ API (батч‑перевірки)
    # ==========================
    def missing_keys(self, keys: Iterable[CallbackData]) -> Iterable[CallbackData]:
        """
        Повертає ітерований набір ключів із `keys`, яких немає у реєстрі.
        Зручно для самотестування у рантаймі.
        """
        return (k for k in keys if k not in self._handlers)					# 🔎 Лінива перевірка відсутніх ключів
