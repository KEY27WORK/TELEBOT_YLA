# 📦 app/bot/handlers/product/product_handler.py
"""
📦 product_handler.py — обробник запуску процесу обробки товару.

🔹 Роль:
    • Приймає URL товару від користувача (повідомлення або аргумент)
    • Валідовує та нормалізує URL (через UrlParserService)
    • За потреби оновлює курси валют (через CurrencyManager)
    • Делегує парсинг/підготовку даних ProductProcessingService
    • Відправляє підготовлені повідомлення через ProductMessenger

✅ Принципи:
    • SRP — клас відповідає тільки за “оркестрацію” обробки запиту користувача
    • DIP — усі залежності інʼєктуються через конструктор (легко тестувати/змінювати)
    • KISS — відсутня зайва логіка, тільки контрольний потік та виклики сервісів

🆕 IMP-011:
    • Використовує строгий результат ProductProcessingResult замість None.
    • При невдачі показує користувачу зрозуміле повідомлення з error_message.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update  # 🤖 Подія/оновлення Telegram
from telegram.constants import ChatAction  # 🖋️ Статус "друкує"

# 🔠 Системні імпорти
import asyncio  # 🔄 Обробка асинхронних відмін
import logging  # 🧾 Логування
from typing import Optional, TYPE_CHECKING  # 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext  # 🧠 Розширений контекст застосунку
from app.bot.ui import static_messages as msg  # 🗒️ Статичні UI-повідомлення
from app.config.setup.constants import AppConstants  # ⚙️ Глобальні константи застосунку
from app.errors.exception_handler_service import ExceptionHandlerService  # 🧯 Єдиний обробник винятків
from app.infrastructure.currency.currency_manager import CurrencyManager  # 💱 Курси валют (оновлення з TTL)
from app.infrastructure.services.product_processing_service import (  # 🛠️ Основний сервіс обробки
    ProductProcessingService,
)
from app.shared.utils.logger import LOG_NAME  # 🏷️ Ім’я логера
from app.shared.utils.url_parser_service import UrlParserService  # 🔗 Валідація/нормалізація URL

if TYPE_CHECKING:
    from app.bot.ui.messengers.product_messenger import ProductMessenger  # ✉️ Відправник блоків про товар

# ================================
# 🧾 НАЛАШТУВАННЯ ЛОГЕРА
# ================================
logger = logging.getLogger(LOG_NAME)  # 🧾 Єдиний логер застосунку


# ================================
# 🏛️ ОБРОБНИК ЗАПИТІВ ПРО ТОВАР
# ================================
class ProductHandler:
    """
    📦 Приймає запит на обробку сторінки товару та делегує його профільним сервісам.
    """

    # ================================
    # ⚙️ ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        currency_manager: CurrencyManager,
        processing_service: ProductProcessingService,
        messenger: "ProductMessenger",
        exception_handler: ExceptionHandlerService,
        constants: AppConstants,
        url_parser_service: UrlParserService,
    ):
        """Ініціалізує залежності обробника.

        Args:
            currency_manager: Менеджер курсів валют (оновлення/читання з кешу).
            processing_service: Сервіс повного циклу обробки URL (парсинг, збагачення, агрегація).
            messenger: Відправник готових блоків повідомлень у Telegram.
            exception_handler: Централізований обробник винятків (логування + UX).
            constants: Глобальні константи застосунку (UI/налаштування).
            url_parser_service: Валідація та нормалізація посилань.
        """
        self.currency_manager = currency_manager  # 💱 Курси валют (оновлення/кеш)
        self.processing_service = processing_service  # 🛠️ Повний процесинг товару
        self.messenger = messenger  # ✉️ Надсилання підготовлених блоків
        self.exception_handler = exception_handler  # 🧯 Єдиний обробник винятків
        self.const = constants  # ⚙️ Константи застосунку/UI
        self.url_parser = url_parser_service  # 🔗 Валідація/нормалізація URL

        logger.info("🔧 ProductHandler ініціалізовано.")  # 🧾 Діагностичний лог

    # ================================
    # 🚀 ПУБЛІЧНИЙ API
    # ================================
    async def handle_url(
        self,
        update: Update,
        context: CustomContext,
        url: Optional[str] = None,
        update_currency: bool = True,
    ) -> None:
        """Основний вхід: приймає URL, виконує процесинг і шле результат."""
        user_id: str = "N/A"  # 🆔 Попереднє значення для логів (на випадок guard'ів)
        final_url: str = ""  # 🔗 Нормалізований URL (може не бути, доки не отримаємо дані)

        try:
            if not update.message:
                return  # 🛑 Немає текстового повідомлення — нічого обробляти

            user_id = getattr(update.effective_user, "id", "N/A")  # 👤 Ідентифікатор користувача
            upd_id = getattr(update, "update_id", "N/A")  # 🏷️ Ідентифікатор апдейта

            # ✅ UX: індикація «друкує»
            try:
                await update.message.chat.send_action(action=ChatAction.TYPING)
            except Exception:
                pass  # 🙈 Не критично — ігноруємо

            message_text = (update.message.text or "").strip()
            final_url = (url or message_text).strip()  # 🔗 Пріоритет аргументу над текстом

            # ✅ Валідація/нормалізація через UrlParserService (з фолбеком)
            try:
                is_valid = self.url_parser.is_valid_url(final_url)  # type: ignore[attr-defined]
            except Exception:
                is_valid = final_url.startswith(("http://", "https://"))

            if not is_valid:
                logger.warning(f"[product] некоректний URL '{final_url}' | user={user_id}")
                await update.message.reply_text(msg.PRODUCT_FETCH_ERROR)
                return

            try:
                final_url = self.url_parser.normalize(final_url)  # type: ignore[attr-defined]
            except Exception:
                pass  # 🪪 Якщо нормалізатор відсутній або впав — працюємо як є

            # ✅ «Розумне» оновлення курсів з TTL
            if update_currency:
                await self.currency_manager.update_all_rates_if_needed()

            logger.info(f"📩 product.handle_url | user={user_id} upd={upd_id} url={final_url}")

            # 1) Процесинг з поверненням строгого Result
            result = await self.processing_service.process_url(final_url)
            if not result.ok:
                # Показуємо користувачу зрозуміле повідомлення з Result
                human_msg = (result.error_message or msg.PRODUCT_FETCH_ERROR)
                await update.message.reply_text(human_msg)

                # Лог: код помилки + первинна причина (не для користувача)
                logger.warning(
                    "product.handle_url fail | code=%s url=%s cause=%r",
                    getattr(result.error_code, "name", "N/A"),
                    final_url,
                    getattr(result, "_cause", None),
                )
                return

            # 2) Повідомлення про визначений регіон
            # Pylance: result.data має тип ProcessedProductData | None.
            # Гарантуємо, що при ok=True data не None, інакше — мʼяко фейлимось.
            if result.data is None:
                logger.error("Invariant violation: result.ok=True, але data=None | url=%s", final_url)
                await update.message.reply_text(msg.PRODUCT_FETCH_ERROR)
                return

            processed_data = result.data  # тепер тип звужено до ProcessedProductData
            region_display = getattr(processed_data, "region_display", "N/A")
            parse_mode = getattr(getattr(self.const, "UI", object()), "DEFAULT_PARSE_MODE", "HTML")
            await update.message.reply_text(
                msg.PRODUCT_REGION_DETECTED.format(region=region_display),
                parse_mode=parse_mode,
            )

            # 3) Надсилання підготовлених блоків через мессенджер
            await self.messenger.send(update, context, processed_data)

        except asyncio.CancelledError:
            logger.info("🛑 ProductHandler cancelled")
            return
        except Exception as e:
            await self.exception_handler.handle(e, update)  # 🧯 Єдине місце обробки помилок
