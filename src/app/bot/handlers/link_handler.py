# 🔗 app/bot/handlers/link_handler.py
"""
🔗 link_handler.py — Головний маршрутизатор для обробки посилань та тексту (Telegram UI‑шар).

Призначення:
- Приймає текст/URL від користувача.
- Для тексту виконує пошук URL товару.
- Якщо є активний режим — делегує відповідному хендлеру.
- Інакше визначає тип URL (товар/колекція) і запускає відповідний обробник.

Архітектура:
- Шар: bot (UI). Жодної бізнес‑логіки — лише оркестрація.
- Залежності входять через конструктор (DI).
"""

# 🌐 ЗОВНІШНІ БІБЛІОТЕКИ
from telegram import Update
from telegram.constants import ChatAction

# 🔠 СИСТЕМНІ ІМПОРТИ
import asyncio
import logging
import re
from functools import wraps
from typing import Awaitable, Callable, Dict, Optional, TYPE_CHECKING, cast

# 🧩 ВНУТРІШНІ МОДУЛІ ПРОЄКТУ
from app.bot.services.custom_context import CustomContext
from app.bot.ui import static_messages as msg
from app.config.setup.constants import AppConstants
from app.domain.products.interfaces import IProductSearchProvider
from app.errors.exception_handler_service import ExceptionHandlerService
from app.infrastructure.currency.currency_manager import CurrencyManager
from app.shared.utils.logger import LOG_NAME
from app.shared.utils.url_parser_service import UrlParserService

if TYPE_CHECKING:
    from app.bot.handlers.price_calculator_handler import PriceCalculationHandler
    from app.bot.handlers.product.collection_handler import CollectionHandler
    from app.bot.handlers.product.product_handler import ProductHandler
    from app.bot.handlers.size_chart_handler_bot import SizeChartHandlerBot
    from app.infrastructure.availability.availability_handler import AvailabilityHandler

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)											# 🧾 Ініціалізуємо іменований логер для єдиного формату логів


# ================================
# 🔎 Типи для хендлерів режимів
# ================================
# Після біндінгу метод екземпляра має сигнатуру (update, context, url)
HandlerMethod = Callable[[Update, CustomContext, str], Awaitable[None]]			# 🧰 Зручний псевдонім типу для методів-обробників режимів
ModeHandlers = Dict[str, HandlerMethod]											# 🧰 Відповідність: ключ режиму → привʼязаний метод


# ================================
# 🔎 Допоміжні функції та декоратори
# ================================
def is_valid_search_query(text: str) -> bool:
    """🧠 Перевіряє, чи схожий текст на валідний пошуковий запит (латиниця/цифри/мінімальні символи)."""
    if len(text or "") < 3:														# 🧪 Мінімальна довжина — щоб відсікти шум
        return False
    allowed_pattern = r"[A-Za-z0-9\s\-\"'/.,&]+"
    if not re.fullmatch(allowed_pattern, text):								# 🧪 Дозволяємо базові ASCII-символи, що часто зустрічаються в назвах
        return False
    if re.search(r"[а-яА-ЯёЁіІїЇєЄ]|[\U0001F600-\U0001F64F]", text):			# 🧪 Відсікаємо кирилицю/емодзі — не придатні для пошуку
        return False
    return True																	# ✅ Валідний пошуковий запит


def product_url_required(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
    """
    🛡️ Декоратор-ґейт: перевіряє, що `url` — це посилання на товар.
    Працює з методами класу (перший прихований аргумент — self).
    """
    @wraps(func)
    async def wrapper(self: "LinkHandler", update: Update, context: CustomContext, url: str) -> None:
        if not update.message:													# 🧯 Страхуємося від відсутності message (наприклад, callback-only апдейти)
            return
        logger.debug("🔒 Перевірка URL на товарний: %s", url)					# 🧾 Діагностика: що саме перевіряємо
        if self.url_parser_service.is_product_url(url):							# ✅ Далі тільки товарні URL
            await func(self, update, context, url)								# 🔀 Пропускаємо виклик до цільового методу
        else:
            await update.message.reply_text(									# 🚫 Пояснюємо користувачу, що посилання не на товар
                msg.URL_NOT_PRODUCT,
                parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
            )

    # Пояснення для тайпчекера: після біндінгу це HandlerMethod
    return cast(Callable[["LinkHandler", Update, CustomContext, str], Awaitable[None]], wrapper)


# ================================
# 🔗 КЛАС-МАРШРУТИЗАТОР ЗАПИТІВ
# ================================
class LinkHandler:
    """
    🔗 Відповідає за прийом текстів/URL, визначення сценарію і делегування в потрібний хендлер.
    Жодної бізнес-логіки — лише координація (UI шар).
    """

    def __init__(
        self,
        *,
        product_handler: "ProductHandler",
        collection_handler: "CollectionHandler",
        size_chart_handler: "SizeChartHandlerBot",
        price_calculator: Optional["PriceCalculationHandler"],					# ← ✅ зробили необовʼязковим
        availability_handler: "AvailabilityHandler",
        search_resolver: IProductSearchProvider,
        url_parser_service: UrlParserService,
        currency_manager: CurrencyManager,
        constants: AppConstants,
        exception_handler: ExceptionHandlerService,
    ) -> None:
        self.product_handler = product_handler									# 🤝 Інʼєкція: обробник товарів
        self.collection_handler = collection_handler								# 🤝 Інʼєкція: обробник колекцій
        self.size_chart_handler = size_chart_handler								# 🤝 Інʼєкція: обробник таблиць розмірів
        self.price_calculator = price_calculator									# 🤝 Інʼєкція: обробник розрахунку ціни (може бути None)
        self.availability_handler = availability_handler							# 🤝 Інʼєкція: обробник мульти-регіональної наявності
        self.search_resolver = search_resolver									# 🤝 Інʼєкція: провайдер пошуку URL за текстом
        self.url_parser_service = url_parser_service								# 🤝 Інʼєкція: сервіс парсингу/класифікації URL
        self.currency_manager = currency_manager									# 🤝 Інʼєкція: менеджер курсів валют
        self.const = constants													# ⚙️ Константи застосунку (UI/logic)
        self._eh = exception_handler												# 🛡️ Глобальний сервіс обробки винятків

        modes = self.const.LOGIC.MODES											# 🗺️ Простір ідентифікаторів режимів
        # Після біндінгу методи мають сигнатуру HandlerMethod — це валідно
        self.mode_handlers: ModeHandlers = {
            modes.REGION_AVAILABILITY: self._handle_region_availability,			# 🌍 Режим «Перевірка наявності»
            modes.PRICE_CALCULATION:   self._handle_price_calculation,			# 🧮 Режим «Розрахунок ціни»
            modes.SIZE_CHART:          self._handle_size_chart,					# 📏 Режим «Таблиця розмірів»
        }

    # ================================
    # 📬 ВХІДНА ТОЧКА
    # ================================
    async def handle_link(self, update: Update, context: CustomContext) -> None:
        """
        📬 Головний метод-оркестратор. Визначає тип запиту і маршрутизує його.
        """
        text = ""
        user_id: str = "unknown"                                               # 🆔 Ідентифікатор користувача для логів
        if not update.message or not update.message.text:						# 🧯 Захист від «порожніх» оновлень
            logger.warning("🚫 Немає повідомлення — ігноруємо оновлення")
            return

        try:
            user_id = getattr(update.effective_user, "id", "unknown")          # 🆔 Запам'ятовуємо ID (навіть якщо далі стане None)
            text = update.message.text.strip()									# ✂️ Нормалізуємо пробіли вхідного тексту
            preview = text if len(text) <= 120 else f"{text[:117]}…"
            logger.info("💬 Отримано повідомлення user=%s: %s", user_id, preview)
            logger.debug("📥 Отримано повідомлення (повністю): %s", text)

            # Best‑effort: індикатор набору (не критично при збої)
            try:
                await update.message.chat.send_action(ChatAction.TYPING)			# 🖐️ Показуємо «друкую...», якщо можливо
            except Exception as e:  # noqa: BLE001
                logger.debug("send_action failed (non‑critical): %s", e, exc_info=True)

            is_url = text.startswith("http")										# 🧪 Дуже простий предикат для URL
            logger.debug("🔗 Це посилання: %s", is_url)

            # Якщо прийшов пошуковий запит — шукаємо URL
            if not is_url:
                url_from_search = await self._handle_search_query(update, context, text)	# 🔍 Отримуємо URL за текстом
                if not url_from_search:											# 🧯 Якщо нічого не знайшли — діалог уже завершено відповіддю
                    return
                text = url_from_search											# 🔁 Далі працюємо як із URL

            # Актуалізуємо курси (якщо падає — не блокуємо користувача)
            try:
                await self.currency_manager.update_all_rates()					# 💱 Підтягнути свіжі курси — корисно для обробників нижче
            except Exception:
                logger.debug(
                    "Не вдалося оновити курси валют (несуттєво для маршрутизації).",
                    exc_info=True,
                )

            # Якщо є активний режим — використовуємо його
            was_routed_by_mode = await self._route_by_mode(update, context, text)	# 🎚️ Перевага за явним режимом користувача
            if was_routed_by_mode:
                return

            # Інакше — визначаємо тип URL
            await self._route_by_url_type(update, context, text)					# 🧠 Автовизначення: товар чи колекція

        except asyncio.CancelledError:
            logger.warning("🔗 LinkHandler: cancelled by upstream.")				# ⛔ Кооперативне скасування — проброс
            raise
        except Exception as e:  # noqa: BLE001
            await self._eh.handle(e, update)										# 🛡️ Єдине місце обробки непередбачуваних помилок

    # ================================
    # 🔎 Обробка пошукового запиту
    # ================================
    async def _handle_search_query(
        self, update: Update, context: CustomContext, query: str
    ) -> Optional[str]:
        """🔍 Обробляє текстовий пошуковий запит та повертає знайдений URL або None."""
        if not update.message:													# 🧯 Дубль-захист від пустого message
            return None

        logger.info("🔍 Пошуковий запит: %s", query)
        logger.debug("🔍 Пошуковий запит (деталі): %s", query)
        if not is_valid_search_query(query):									# 🚫 Миттєво відкидаємо «сміття»
            logger.warning("⚠️ Некоректний запит: %s", query)
            await update.message.reply_text(
                msg.SEARCH_INVALID_QUERY,
                parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
            )
            return None

        await update.message.reply_text(										# ⏳ Даємо фідбек, що шукаємо
            msg.SEARCH_IN_PROGRESS,
            parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
        )
        found_url_obj = await self.search_resolver.resolve_one(query)			# 🔎 Власне пошук через провайдер
        found_url = str(found_url_obj) if found_url_obj else None
        logger.info("🔗 Знайдений URL: %s", found_url)
        logger.debug("🔗 Результат пошуку: %s", found_url_obj)

        if not found_url:														# 😕 Нічого не знайшли — кажемо прямо
            await update.message.reply_text(
                msg.SEARCH_NO_RESULTS,
                parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
            )
            return None

        return found_url														# ✅ Повертаємо URL для подальшої маршрутизації

    # ================================
    # 🎛️ Маршрутизація за активним режимом
    # ================================
    async def _route_by_mode(self, update: Update, context: CustomContext, url: str) -> bool:
        """Пробує маршрутизувати запит відповідно до активного режиму користувача."""
        mode = context.mode														# 🎚️ Який режим зараз у користувача
        if not mode:															# ⛔ Режим не заданий — пропускаємо
            logger.debug("🎚️ Активний режим відсутній")
            return False

        logger.info("🎚️ Активний режим користувача: %s", mode)
        logger.debug("🎚️ Активний режим (debug): %s", mode)

        handler_method = self.mode_handlers.get(mode)							# 🔑 Дістаємо відповідний обробник
        if not handler_method:													# ⛔ Немає мапінгу на метод — пропускаємо
            return False

        logger.info(
            "➡️ Викликаємо обробник режиму %s → %s",
            mode,
            getattr(handler_method, "__name__", "N/A"),
        )
        logger.debug("➡️ Викликаємо обробник режиму: %s", getattr(handler_method, "__name__", "N/A"))
        await handler_method(update, context, url)								# ▶️ Виконуємо конкретний сценарій
        return True																# ✅ Так, ми відмаршрутизували за режимом

    # ================================
    # 🧠 Маршрутизація за типом URL
    # ================================
    async def _route_by_url_type(self, update: Update, context: CustomContext, url: str) -> None:
        """Визначає тип URL (товар чи колекція) і викликає відповідний обробник."""
        if not update.message:													# 🧯 Без message немає кому відповідати
            return

        is_collection = self.url_parser_service.is_collection_url(url)			# 🧪 Перевіряємо, чи це сторінка колекції
        is_product = self.url_parser_service.is_product_url(url)					# 🧪 Чи це сторінка товару
        logger.debug("🔎 is_collection=%s, is_product=%s", is_collection, is_product)

        modes = self.const.LOGIC.MODES											# 🗺️ Коротке посилання на константи режимів

        if is_collection:
            logger.info("📚 Автоматично розпізнано колекцію: %s", url)
            context.mode = modes.COLLECTION										# 📌 Виставляємо режим «Колекція»
            context.url = url													# 🔗 Зберігаємо URL у контексті
            await update.message.reply_text(
                msg.COLL_START,
                parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
            )
            await self.collection_handler.handle_collection(update, context)		# ▶️ Запускаємо обробник колекції
            return

        if is_product:
            logger.info("🛍️ Автоматично розпізнано товар: %s", url)
            context.mode = modes.PRODUCT										# 📌 Виставляємо режим «Товар»
            await update.message.reply_text(
                msg.PRODUCT_START_PROCESSING,
                parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
            )
            # Курси вже оновлені вище — не змушуємо вдруге
            await self.product_handler.handle_url(update, context, url=url, update_currency=False)
            return

        logger.warning("❓ Не вдалося розпізнати URL: %s", url)					# 🤷 Невідомий формат посилання
        await update.message.reply_text(
            msg.URL_NOT_RECOGNIZED,
            parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
        )

    # ================================
    # 🌍 РЕЖИМ: мульти-регіональна перевірка
    # ================================
    @product_url_required
    async def _handle_region_availability(self, update: Update, context: CustomContext, url: str) -> None:
        if not update.message:													# 🧯 Дубль-захист
            return
        logger.info("🌍 Запит перевірки наявності для: %s", url)
        await update.message.reply_text(
            msg.AVAILABILITY_IN_PROGRESS,
            parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
        )
        await self.availability_handler.handle_availability(update, context, url=url)	# ▶️ Делегуємо обробнику наявності

    # ================================
    # 🧮 РЕЖИМ: розрахунок ціни
    # ================================
    @product_url_required
    async def _handle_price_calculation(self, update: Update, context: CustomContext, url: str) -> None:
        if not update.message:													# 🧯 Дубль-захист
            return
        # 🔒 Акуратний фолбэк, якщо модуль не підключено в DI
        if not self.price_calculator:
            await update.message.reply_text(
                "❌ Модуль розрахунку ціни наразі не підключений.",
                parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
            )
            return

        logger.info("🧮 Запит розрахунку ціни для: %s", url)
        await update.message.reply_text(
            msg.PRICE_CALC_IN_PROGRESS,
            parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
        )
        await self.price_calculator.handle_price_calculation(update, context, url=url)	# ▶️ Делегуємо калькулятору

    # ================================
    # 📏 РЕЖИМ: таблиця розмірів
    # ================================
    @product_url_required
    async def _handle_size_chart(self, update: Update, context: CustomContext, url: str) -> None:
        if not update.message:													# 🧯 Дубль-захист
            return
        logger.info("📏 Запит таблиці розмірів для: %s", url)
        await update.message.reply_text(
            msg.SIZE_CHART_IN_PROGRESS,
            parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
        )
        await self.size_chart_handler.size_chart_command(update, context, url=url)	# ▶️ Делегуємо генератору size chart
