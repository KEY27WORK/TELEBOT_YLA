# 🎛️ app/bot/handlers/callback_handler.py
"""
🎛️ callback_handler.py — централізований обробник для всіх inline‑кнопок (callback_query).

Призначення:
- Приймає натискання на inline‑кнопки.
- Безпечно парсить payload через `CallbackData`.
- Кладе параметри в `context.callback_params`.
- Делегує виконання зареєстрованому хендлеру з `CallbackRegistry`.
- Всі помилки йдуть у централізований `ExceptionHandlerService`.

Архітектура:
- Шар: bot (UI Telegram). Жодної бізнес‑логіки.
- Залежності приходять через конструктор (DI).
"""

# ==========================
# 🌐 ЗОВНІШНІ БІБЛІОТЕКИ
# ==========================
from telegram import Update													# 📦 Тип апдейту Telegram

# ==========================
# 🔠 СИСТЕМНІ ІМПОРТИ
# ==========================
import asyncio														# 🔄 Корутини / CancelledError
import logging														# 🧾 Логування
from typing import Awaitable, Callable, Optional						# 🧰 Типізація колбеків

# ==========================
# 🧩 ВНУТРІШНІ МОДУЛІ
# ==========================
from app.bot.services.callback_data_factory import CallbackData			# 🧩 Парсинг та валідація payload
from app.bot.services.callback_registry import CallbackRegistry			# 📚 Реєстр колбек‑хендлерів
from app.bot.services.custom_context import CustomContext				# 🧱 Розширений контекст застосунку
from app.errors.exception_handler_service import ExceptionHandlerService	# 🚑 Централізована обробка помилок
from app.shared.utils.logger import LOG_NAME							# 🏷️ Імʼя логера проєкту

# ==========================
# 🧾 ЛОГЕР
# ==========================
logger = logging.getLogger(LOG_NAME)										# 🧾 Глобальний логер модуля


# ==========================
# 🏛️ КЛАС ОБРОБНИКА
# ==========================
class CallbackHandler:
    """
    🎛️ Централізовано обробляє натискання на inline‑кнопки.

    Вхідні залежності:
        registry: реєстр відповідностей (ключ callback → обробник).
        exception_handler: централізований сервіс обробки винятків.

    Примітка:
        Клас не містить бізнес‑логіки; тільки парсинг і делегування.
    """

    def __init__(self, registry: CallbackRegistry, exception_handler: ExceptionHandlerService) -> None:
        self.registry = registry												# 📚 DI: реєстр колбек‑хендлерів
        self._eh = exception_handler											# 🚑 DI: сервіс обробки винятків

    # ==========================
    # 🎯 ГОЛОВНИЙ МЕТОД
    # ==========================
    async def handle(self, update: Update, context: CustomContext) -> None:
        """
        Приймає callback_query, парсить дані та викликає відповідний обробник.

        Args:
            update: апдейт Telegram.
            context: кастомний контекст застосунку.
        """
        query = update.callback_query											# ✉️ Сам обʼєкт callback_query
        if not query or not query.data:
            return																# 🚫 Немає даних — нічого обробляти

        try:
            # Best‑effort: прибрати «годинник» на кнопці
            try:
                await query.answer()												# ✅ Миттєва відповідь користувачу
            except Exception as e:  # noqa: BLE001
                logger.debug("Callback answer failed (non‑critical): %s", e, exc_info=True)	# ℹ️ Не критично — просто лог

            raw_data = query.data												# 🧾 Сирий payload з кнопки
            logger.info("👆 Callback received: %s", raw_data)					# 📝 Записуємо факт натискання

            # 🧩 Безпечний розбір даних
            try:
                key, params = CallbackData.parse(raw_data)						# 🔍 Валідація та парсинг payload
                context.callback_params = params								# 📦 Кладемо параметри в контекст
                logger.debug("🧩 Parsed: key='%s', params=%s", key.id(), params)	# 🔎 Для дебагу: що саме розібрали
            except (ValueError, IndexError) as e:
                logger.warning("⚠️ Failed to parse callback_data '%s': %s", raw_data, e)	# ⚠️ Некоректний payload — ігноруємо
                return

            # 🔎 Пошук хендлера в реєстрі
            handler: Optional[Callable[[Update, CustomContext], Awaitable[None]]] = self.registry.get_handler(key)	# 🗂️ Отримуємо зареєстрований обробник
            if not handler:
                logger.warning("⚠️ Handler for callback '%s' not found.", key.id())		# ⚠️ Ключ не зареєстрований
                return

            # ▶️ Делегування виконання
            await handler(update, context)										# 🎬 Викликаємо потрібний хендлер

        except asyncio.CancelledError:
            logger.warning("Callback handling cancelled.")							# ⏹️ Завдання скасоване — передаємо далі
            raise
        except Exception as e:  # noqa: BLE001
            await self._eh.handle(e, update)									# 🚑 Централізована обробка будь‑яких винятків
