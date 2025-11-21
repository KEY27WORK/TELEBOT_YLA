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
import contextlib  # 🛡️ Безпечне подавлення винятків у побічних діях
import logging  # 🧾 Логування
from dataclasses import dataclass  # 🧱 DTO для підготовлених карток
from typing import Optional, Sequence, TYPE_CHECKING  # 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext  # 🧠 Розширений контекст застосунку
from app.bot.ui import static_messages as msg  # 🗒️ Статичні UI-повідомлення
from app.config.setup.constants import AppConstants  # ⚙️ Глобальні константи застосунку
from app.errors.exception_handler_service import ExceptionHandlerService  # 🧯 Єдиний обробник винятків
from app.infrastructure.currency.currency_manager import CurrencyManager  # 💱 Курси валют (оновлення з TTL)
from app.infrastructure.services.product_processing_service import (  # 🛠️ Основний сервіс обробки
    ProcessingErrorCode,
    ProcessedProductData,
    ProductProcessingResult,
    ProductProcessingService,
)
from app.infrastructure.services.product_media_preparer import (  # 🖼️ Підготовка стеку фото
    PreparedMediaStack,
    ProductMediaPreparer,
    ProductMediaPreparationError,
)
from app.shared.utils.logger import LOG_NAME  # 🏷️ Ім’я логера
from app.shared.utils.url_parser_service import UrlParserService  # 🔗 Валідація/нормалізація URL
from .image_sender import MediaRef  # 🖼️ Типи медіа, які приймає ImageSender

if TYPE_CHECKING:
    from app.bot.ui.messengers.product_messenger import ProductMessenger  # ✉️ Відправник блоків про товар

# ================================
# 🧾 НАЛАШТУВАННЯ ЛОГЕРА
# ================================
logger = logging.getLogger(LOG_NAME)  # 🧾 Єдиний логер застосунку


@dataclass(slots=True)
class PreparedProductCard:
    """📦 Обʼєднує результат процесингу з готовими медіа."""

    result: ProductProcessingResult
    media_stack: Optional[Sequence[MediaRef]] = None

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
        media_preparer: ProductMediaPreparer,
        exception_handler: ExceptionHandlerService,
        constants: AppConstants,
        url_parser_service: UrlParserService,
    ):
        """Ініціалізує залежності обробника.

        Args:
            currency_manager: Менеджер курсів валют (оновлення/читання з кешу).
            processing_service: Сервіс повного циклу обробки URL (парсинг, збагачення, агрегація).
            messenger: Відправник готових блоків повідомлень у Telegram.
            media_preparer: Відповідає за завантаження/валідацію фото перед надсиланням.
            exception_handler: Централізований обробник винятків (логування + UX).
            constants: Глобальні константи застосунку (UI/налаштування).
            url_parser_service: Валідація та нормалізація посилань.
        """
        self.currency_manager = currency_manager  # 💱 Курси валют (оновлення/кеш)
        self.processing_service = processing_service  # 🛠️ Повний процесинг товару
        self.messenger = messenger  # ✉️ Надсилання підготовлених блоків
        self.media_preparer = media_preparer  # 🖼️ Готує стек фото
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
        *,
        send_immediately: bool = True,
    ) -> Optional[PreparedProductCard]:
        """Основний вхід: приймає URL, виконує процесинг і (опційно) надсилає результат."""
        user_id: str = "N/A"
        final_url: str = ""

        try:
            if not update.message:
                return None  # 🛑 Без message не можемо відповідати

            user_id = getattr(update.effective_user, "id", "N/A")
            upd_id = getattr(update, "update_id", "N/A")

            if send_immediately:
                with contextlib.suppress(Exception):
                    await update.message.chat.send_action(action=ChatAction.TYPING)

            message_text = (update.message.text or "").strip()
            final_url = (url or message_text).strip()
            if not final_url:
                if send_immediately:
                    await update.message.reply_text(msg.PRODUCT_FETCH_ERROR)
                return None

            try:
                is_valid = self.url_parser.is_valid_url(final_url)  # type: ignore[attr-defined]
            except Exception:
                is_valid = final_url.startswith(("http://", "https://"))

            if not is_valid:
                logger.warning("[product] некоректний URL '%s' | user=%s", final_url, user_id)
                if send_immediately:
                    await update.message.reply_text(msg.PRODUCT_FETCH_ERROR)
                return None

            with contextlib.suppress(Exception):
                final_url = self.url_parser.normalize(final_url)  # type: ignore[attr-defined]

            if update_currency:
                await self.currency_manager.update_all_rates_if_needed()

            logger.info("📩 product.handle_url | user=%s upd=%s url=%s", user_id, upd_id, final_url)

            processing_result = await self.processing_service.process_url(final_url)
            prepared_card = PreparedProductCard(result=processing_result)

            if not processing_result.ok:
                if send_immediately:
                    human_msg = processing_result.error_message or msg.PRODUCT_FETCH_ERROR
                    await update.message.reply_text(human_msg)
                logger.warning(
                    "product.handle_url fail | code=%s url=%s cause=%r",
                    getattr(processing_result.error_code, "name", "N/A"),
                    final_url,
                    getattr(processing_result, "_cause", None),
                )
                return prepared_card

            data = processing_result.data
            if data is None:
                logger.error("Invariant violation: result.ok=True, але data=None | url=%s", final_url)
                failure = ProductProcessingResult.fail(
                    ProcessingErrorCode.UnexpectedError,
                    "Не вдалося сформувати дані товару.",
                )
                if send_immediately:
                    await update.message.reply_text(msg.PRODUCT_FETCH_ERROR)
                return PreparedProductCard(failure)

            validation_error = self._validate_card_ready(data)
            if validation_error:
                failure = ProductProcessingResult.fail(
                    ProcessingErrorCode.CardValidationFailed,
                    validation_error,
                    data=data,
                )
                if send_immediately:
                    reply_text = (
                        self._build_admin_failure_message(failure)
                        if self._should_show_admin_details(context)
                        else msg.PRODUCT_CARD_INCOMPLETE
                    )
                    await update.message.reply_text(reply_text)
                logger.warning("product.card_validation_failed | url=%s reason=%s", final_url, validation_error)
                return PreparedProductCard(failure)

            try:
                media_stack = await self._prepare_media_stack(data)
            except ProductMediaPreparationError as exc:
                failure = ProductProcessingResult.fail(
                    ProcessingErrorCode.MediaPreparationFailed,
                    str(exc),
                    cause=exc,
                    data=data,
                )
                if send_immediately:
                    await update.message.reply_text(msg.PRODUCT_MEDIA_FAILED)
                logger.warning("product.media_prepare_failed | url=%s reason=%s", final_url, exc)
                return PreparedProductCard(failure)

            prepared_card = PreparedProductCard(processing_result, media_stack)

            if send_immediately:
                try:
                    await self.send_prepared_card(update, context, prepared_card, include_region_notice=True)
                except ProductMediaPreparationError as exc:
                    failure = ProductProcessingResult.fail(
                        ProcessingErrorCode.MediaPreparationFailed,
                        str(exc) or "Не вдалося надіслати фото товару.",
                        cause=exc,
                        data=data,
                    )
                    if send_immediately:
                        await update.message.reply_text(msg.PRODUCT_MEDIA_FAILED)
                    logger.warning("product.media_send_failed | url=%s reason=%s", final_url, exc)
                    return PreparedProductCard(failure)

            return prepared_card

        except asyncio.CancelledError:
            logger.info("🛑 ProductHandler cancelled")
            return None
        except Exception as exc:  # noqa: BLE001
            await self.exception_handler.handle(exc, update)
            return None

    async def send_prepared_card(
        self,
        update: Update,
        context: CustomContext,
        prepared_card: PreparedProductCard,
        *,
        include_region_notice: bool = False,
    ) -> None:
        """Надсилає вже підготовлений результат (використовується в колекціях)."""
        data = prepared_card.result.data
        if data is None:
            logger.error("send_prepared_card called без даних")
            return

        media_stack = prepared_card.media_stack
        if not media_stack:
            raise ProductMediaPreparationError("Порожній стек медіа для надсилання")

        parse_mode = getattr(getattr(self.const, "UI", object()), "DEFAULT_PARSE_MODE", "HTML")
        if include_region_notice and update.message:
            region_display = getattr(data, "region_display", "N/A")
            with contextlib.suppress(Exception):
                await update.message.reply_text(
                    msg.PRODUCT_REGION_DETECTED.format(region=region_display),
                    parse_mode=parse_mode,
                )

        try:
            await self.messenger.send(update, context, data, media_stack=media_stack)
        except ProductMediaPreparationError as exc:
            failure = ProductProcessingResult.fail(
                ProcessingErrorCode.MediaPreparationFailed,
                str(exc) or "Не вдалося надіслати фото товару.",
                cause=exc,
                data=data,
            )
            prepared_card.result = failure
            logger.warning("product.media_send_failed | url=%s reason=%s", data.url, exc)
            raise

    def _validate_card_ready(self, data: ProcessedProductData) -> Optional[str]:
        """Перевіряє, що всі критичні блоки картки присутні."""
        content = data.content
        missing: list[str] = []

        if not (content.title or "").strip():
            missing.append("title")
        if not (content.slogan or "").strip():
            missing.append("slogan")
        if not (content.colors_text or "").strip():
            missing.append("availability")
        if not (content.price_message or "").strip():
            missing.append("price")
        if not content.images:
            missing.append("photos")

        if missing:
            return "Відсутні критичні блоки: " + ", ".join(missing)
        return None

    async def _prepare_media_stack(self, data: ProcessedProductData) -> Sequence[MediaRef]:
        """Викачує та повертає стек фото у вигляді InputFile."""
        stack: PreparedMediaStack = await self.media_preparer.prepare_stack(
            data.content.images,
            title=data.content.title or data.url,
        )
        if not stack.files:
            raise ProductMediaPreparationError("Не вдалося підготувати жодного фото товару.")
        return tuple(stack.files)

    def _should_show_admin_details(self, context: CustomContext) -> bool:
        """Визначаємо, чи показувати розгорнуте пояснення адміну."""
        try:
            mode = context.mode
        except AttributeError:
            return True
        if not mode:
            return True
        return mode == self.const.LOGIC.MODES.PRODUCT

    def _build_admin_failure_message(self, failure: ProductProcessingResult) -> str:
        """Формує розгорнуте пояснення, чому картка не готова."""
        lines: list[str] = [msg.PRODUCT_CARD_INCOMPLETE, "", msg.PRODUCT_CARD_ADMIN_REASON_HEADER]
        data = failure.data
        diag = getattr(data, "diagnostics", None) if data else None
        if not diag:
            lines.append(msg.PRODUCT_CARD_ADMIN_NO_DIAGNOSTICS)
            return "\n".join(lines)

        images_total = getattr(diag, "images_total", getattr(diag, "images_count", 0))
        images_ready = getattr(diag, "images_ready", getattr(diag, "images_count", 0))
        images_error = getattr(diag, "images_error", None)
        if images_total == 0:
            lines.append("• Фото: не вдалося знайти жодного зображення на сайті.")
        elif images_ready == 0:
            reason = images_error or "жодне зображення не пройшло підготовку."
            lines.append(f"• Фото: знайдено {images_total}, але нічого не підготовлено ({reason})")
        elif images_ready < images_total or images_error:
            reason = images_error or "частина зображень відфільтрована."
            lines.append(f"• Фото: підготовлено {images_ready} з {images_total}. {reason}")

        if not getattr(diag, "hashtags_ok", True):
            reason = getattr(diag, "hashtags_error", None) or "невідома помилка генерації."
            if getattr(diag, "ai_quota_problem", False):
                reason = "OpenAI rate limit / квота. Схоже, закінчився баланс."
            lines.append(f"• Хештеги: {reason}")

        if not getattr(diag, "music_ok", True):
            reason = getattr(diag, "music_error", None) or "музика не згенерована."
            lines.append(f"• Музика: {reason}")

        if not getattr(diag, "has_size_chart", False):
            reason = getattr(diag, "size_chart_error", None) or "таблицю не знайдено або вона не пройшла OCR."
            lines.append(f"• Таблиця розмірів: {reason}")

        if getattr(diag, "ai_quota_problem", False):
            ai_note = getattr(diag, "ai_error_raw", None) or "OpenAI повернув помилку квоти/RateLimit."
            lines.append(f"• OpenAI: {ai_note}")

        return "\n".join(lines)
