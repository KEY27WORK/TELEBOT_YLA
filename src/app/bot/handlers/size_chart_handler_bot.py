# 📏 app/bot/handlers/size_chart_handler_bot.py
"""
📏 size_chart_handler_bot.py — Обробник команди для генерації таблиць розмірів.

🔹 Клас `SizeChartHandlerBot`:
    • Отримує посилання або HTML-сторінку товару
    • Завантажує HTML при необхідності (через парсер)
    • Делегує обробку таблиць сервісу SizeChartService
    • Відправляє зображення через SizeChartMessenger
"""

# 🌐 Зовнішні бібліотеки (Telegram)
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest, RetryAfter, NetworkError

# 🔠 Системні імпорти
import asyncio
import logging
from typing import Optional, List

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext
from app.bot.ui import static_messages as msg
from app.bot.ui.messengers.size_chart_messenger import SizeChartMessenger
from app.config.setup.constants import AppConstants
from app.domain.size_chart.interfaces import SizeChartArtifacts
from app.errors.exception_handler_service import ExceptionHandlerService
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.infrastructure.size_chart.size_chart_service import SizeChartService
from app.shared.utils.logger import LOG_NAME


# ==========================
# 🧾 ЛОГЕР
# ==========================
logger = logging.getLogger(LOG_NAME)												# 🧾 Іменований логер проєкту


# ==========================
# ⚙️ НАЛАШТУВАННЯ ТАЙМАУТІВ
# ==========================
# За потреби ці значення можна винести в AppConstants або config.yaml
_PARSER_TIMEOUT_SEC = 25															# ⏱️ Ліміт на завантаження HTML парсером
_SIZECHART_TIMEOUT_SEC = 45															# ⏱️ Ліміт на обробку всіх таблиць розмірів


# ==========================
# 🏛️ ОБРОБНИК ТАБЛИЦЬ РОЗМІРІВ
# ==========================
class SizeChartHandlerBot:
    """Координує завантаження HTML, OCR/генерацію та надсилання таблиць розмірів."""

    def __init__(
        self,
        parser_factory: ParserFactory,
        size_chart_service: SizeChartService,
        messenger: SizeChartMessenger,
        exception_handler: ExceptionHandlerService,
        constants: AppConstants,
    ) -> None:
        """
        Args:
            parser_factory: фабрика парсерів продукту.
            size_chart_service: сервіс OCR/генерації таблиць.
            messenger: відправник готових зображень.
            exception_handler: централізований обробник винятків.
            constants: константи додатку (parse_mode тощо).
        """
        self.parser_factory = parser_factory											# 🏭 DI: фабрика парсерів (створює товарний парсер)
        self.size_chart_service = size_chart_service									# 🧠 DI: сервіс пошуку/розпізнавання таблиць
        self.messenger = messenger													# ✉️ DI: шар відправки зображень у Telegram
        self._exception_handler = exception_handler									# 🛡️ DI: єдина точка обробки помилок Telegram/бізнес‑логіки
        self._const = constants														# ⚙️ DI: константи (у т.ч. parse_mode)

    # ==========================
    # 🔓 ПУБЛІЧНИЙ МЕТОД
    # ==========================
    async def size_chart_command(
        self,
        update: Update,
        context: CustomContext,
        url: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> None:
        """
        Точка входу: приймає URL або сирий HTML (page_source), генерує таблиці та шле користувачу.
        """
        if not update.message:														# 🚧 Команда прийшла не з message (наприклад, callback) — нічого не робимо
            return

        chat_id = update.effective_chat.id if update.effective_chat else "N/A"		# 🆔 Ідентифікатор чату для логів
        log_extra = {"chat_id": chat_id, "url": url or "inline"}						# 🧾 Додатковий контекст логування

        try:
            # Показати індикатор набору, але не ламати ланцюг у разі помилки
            try:
                await update.message.chat.send_action(ChatAction.TYPING)				# 🖐️ UX: показуємо, що бот працює
            except Exception:														# 🤷 Несуттєві збої Telegram тут ігноруємо
                pass

            # 1) Джерело URL
            args = getattr(context, "args", None) or []								# 🧰 Безпечне отримання аргументів команди
            final_url = url or (args[0] if args else None)							# 🔗 Пріоритет: явний url аргумент → перший аргумент з /команди
            if not final_url and not page_source:									# ❓ Немає ні URL, ні сирого HTML — просимо посилання
                await self._send_text_safe(update, context, msg.SIZE_CHART_URL_REQUIRED)
                return

            # 2) Якщо немає HTML — завантажити з сайту через парсер (з таймаутом)
            if not page_source and final_url:
                await self._send_text_safe(update, context, msg.SIZE_CHART_LOADING_PAGE)	# ℹ️ Повідомляємо про старт завантаження сторінки
                parser = self.parser_factory.create_product_parser(						# 🏭 Створюємо парсер товару без прогрес‑бару
                    final_url,
                    enable_progress=False
                )

                try:
                    await asyncio.wait_for(												# ⏱️ Гарантований ліміт часу на парсинг сторінки
                        parser.get_product_info(),
                        timeout=_PARSER_TIMEOUT_SEC,
                    )
                except asyncio.TimeoutError:
                    logger.warning("⏳ Parser timeout", extra=log_extra)					# 🧾 Лог: парсер не встиг за відведений час
                    await self._send_text_safe(update, context, msg.SIZE_CHART_PAGE_LOAD_FAILED)
                    return

                page_source = parser.page_source											# 📄 Беремо сирий HTML зі створеного парсера

            if not page_source:															# 🟥 Навіть після спроби завантаження немає HTML
                await self._send_text_safe(update, context, msg.SIZE_CHART_PAGE_LOAD_FAILED)
                return

            # 3) Обробити всі таблиці (з таймаутом)
            await self._send_text_safe(update, context, msg.SIZE_CHART_IN_PROGRESS)		# 🔧 Старт обробки таблиць (OCR/генерація)

            product_sku = self._extract_product_sku(final_url or (args[0] if args else None))	# 🆔 Витягуємо артикул товару (URL чи прямий ввід)
            try:
                artifacts = await asyncio.wait_for(										# 🖼️ Отримуємо структурований результат
                    self.size_chart_service.process_all_size_charts(
                        page_source,
                        product_sku=product_sku,
                    ),
                    timeout=_SIZECHART_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                logger.warning("⏳ SizeChart processing timeout", extra=log_extra)			# 🧾 Лог: обробка таблиць тривала надто довго
                await self._send_text_safe(update, context, msg.SIZE_CHART_FAILED)
                return

            # 4) Надіслати результат
            image_paths = artifacts.ordered_paths()
            if not image_paths:
                await self._send_text_safe(update, context, msg.SIZE_CHART_FAILED)
                return

            summary_text = self._format_size_chart_summary(artifacts)
            if summary_text:
                await self._send_text_safe(update, context, summary_text)

            await self.messenger.send(update, context, image_paths)						# ✉️ Відправляємо всі зображення користувачу  ✅ FIX: додано context

        except asyncio.CancelledError:													# ⛔ Коректна відміна таска — не ковтаємо
            logger.warning("📏 SizeChart: cancelled", extra=log_extra)
            raise
        except (RetryAfter, BadRequest, NetworkError) as e:								# 📡 Telegram‑помилки: централізовано
            await self._exception_handler.handle(e, update)
        except Exception as e:  # noqa: BLE001											# 🧯 Будь‑які інші збої — також через централізований хендлер
            await self._exception_handler.handle(e, update)

    # ==========================
    # 🧰 ДОПОМІЖНЕ
    # ==========================
    @staticmethod
    def _extract_product_sku(source: Optional[str]) -> Optional[str]:
        """Пробує витягнути артикул (SKU) з URL або сирого рядка."""

        if not isinstance(source, str):
            return None

        raw = source.strip()
        if not raw:
            return None

        candidate = raw
        if "://" in raw:
            path_part = raw.split("://", 1)[1]
            candidate = path_part.rsplit("/", 1)[-1]

        candidate = candidate.split("?", 1)[0].split("#", 1)[0].strip()

        return candidate or None

    async def _send_text_safe(
        self,
        update: Update,
        context: CustomContext,
        text: str,
        *,
        parse_mode: Optional[str] = None,
    ) -> None:
        """Відправляє текст: спочатку reply, у разі неможливості — bot.send_message."""
        try:
            if update.message:															# 💬 Звичайна відповідь у реплай
                await update.message.reply_text(
                    text=text,
                    parse_mode=parse_mode or self._const.UI.DEFAULT_PARSE_MODE,
                )
                return
            if update.effective_chat:													# 📨 Фолбек: пряме відправлення у чат
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    parse_mode=parse_mode or self._const.UI.DEFAULT_PARSE_MODE,
                )
        except Exception as e:  # best‑effort, не валимо основний сценарій				# 🟡 Відправка службових повідомлень — безпечний режим
            logger.debug("⚠️ Не вдалося надіслати службове повідомлення: %s", e, exc_info=True)

    def _format_size_chart_summary(self, artifacts: SizeChartArtifacts) -> Optional[str]:
        """📄 Готує коротке резюме по знайдених таблицях."""
        parts: List[str] = []
        if artifacts.product_tables:
            parts.append(f"🧵 Унікальні таблиці: {len(artifacts.product_tables)}")
        if artifacts.global_tables:
            parts.append(f"🌐 Загальні таблиці: {len(artifacts.global_tables)}")
        extra_total = sum(len(paths) for paths in artifacts.extra_tables.values())
        if extra_total:
            parts.append(f"🧩 Додаткові таблиці: {extra_total}")
        if not parts:
            return None
        return "📏 Знайдено таблиці розмірів:\n" + "\n".join(parts)