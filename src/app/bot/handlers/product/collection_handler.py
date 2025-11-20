# 🧾 app/bot/handlers/product/collection_handler.py
"""
🧾 CollectionHandler — тонкий UI‑оркестратор обробки колекцій:
- валідація посилання;
- службові повідомлення (start/region/progress/done);
- делегація в CollectionRunner;
- безпечні (непадаючі) редагування повідомлень прогресу.

Дотримано DI: зовнішні сервіси передаються через конструктор.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Message, Update                                       # 📲 Telegram типи для повідомлень

# 🔠 Системні імпорти
import asyncio                                                             # ⏳ Асинхронні затримки/таски
import contextlib                                                          # 🧯 Безпечне придушення винятків
import logging                                                             # 🧾 Логування
from typing import List, Optional                                          # 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.product_handler import ProductHandler        # 🛍️ Обробник одиничного товару
from app.bot.services.custom_context import CustomContext                  # 🧠 Розширений контекст бота
from app.bot.ui import static_messages as msg                              # 📝 Статичні текстові повідомлення
from app.config.setup.constants import AppConstants                        # ⚙️ Константи застосунку
from app.errors.exception_handler_service import ExceptionHandlerService   # 🧯 Централізований хендлер винятків
from app.infrastructure.collection_processing.collection_processing_service import (
    CollectionProcessingService,
)                                                                          # 🧵 Сервіс збору посилань з колекції
from app.domain.products.entities import Url                               # 🔗 Value-object посилання продукту
from app.shared.utils.logger import LOG_NAME                               # 🏷️ Ім'я логера
from app.shared.utils.url_parser_service import UrlParserService           # 🔎 Парсер/валідація URL + регіон
from .collection_runner import (                                           # 🏃 Оркестратор багатопотокової обробки
    CollectionItemState,
    CollectionItemStatus,
    CollectionProgressSnapshot,
    CollectionRunner,
)


# ==========================
# 🧾 ЛОГЕР
# ==========================
logger = logging.getLogger(LOG_NAME)


# ==========================
# 🏛️ КЛАС ОБРОБНИКА
# ==========================
class CollectionHandler:
    """Оркестрація UI навколо обробки колекції."""

    _STATUS_ICONS = {
        CollectionItemState.PENDING: "⚪️",
        CollectionItemState.PROCESSING: "⏳",
        CollectionItemState.RETRYING: "🟡",
        CollectionItemState.OK: "🟢",
        CollectionItemState.FAILED: "🔴",
    }

    # --------------------------
    # ⚙️ ІНІЦІАЛІЗАЦІЯ
    # --------------------------
    def __init__(
        self,
        product_handler: ProductHandler,
        url_parser_service: UrlParserService,
        collection_processing_service: CollectionProcessingService,
        exception_handler: ExceptionHandlerService,
        constants: AppConstants,
        *,
        max_items: Optional[int] = 50,
        concurrency: int = 4,
        per_item_retries: int = 2,
    ) -> None:
        self._url_parser = url_parser_service									# 🔎 Сервіс валідації/розбору URL та визначення регіону
        self._proc_service = collection_processing_service						# 🧵 Джерело посилань товарів із сторінки колекції
        self._exception_handler = exception_handler							# 🧯 Єдина точка обробки винятків
        self._const = constants											# ⚙️ Константи застосунку (UI/логіка/ліміти)

        # М'яке читання блоків із констант (не ламаємо старі конфіги)
        coll_cfg = getattr(getattr(self._const, "COLLECTION", object()), "__dict__", {})	# 🧩 Опційний неймспейс COLLECTION
        self._max_items = (
            getattr(self._const, "COLLECTION_MAX_ITEMS", None)
            or coll_cfg.get("MAX_ITEMS", max_items)
        )															# 🔢 Глобальний ліміт на кількість елементів у запуску
        eff_concurrency = coll_cfg.get("CONCURRENCY", concurrency)				# 🧵 Паралелізм обробки
        eff_retries = coll_cfg.get("PER_ITEM_RETRIES", per_item_retries)			# ♻️ Ретрай на елемент
        eff_progress_sec = coll_cfg.get("PROGRESS_INTERVAL_SEC", 2.5)			# ⏱️ Частота оновлень прогресу

        self._runner = CollectionRunner(
            product_handler=product_handler,								# 🛍️ Делегуємо кожну картку товару в ProductHandler
            concurrency=eff_concurrency,								# 🧵 Скільки одночасних воркерів
            per_item_retries=eff_retries,								# ♻️ Скільки спроб для одного товару
            progress_interval_sec=eff_progress_sec,						# ⏱️ Дельта між апдейтами прогресу
        )
        logger.info(
            "🧾 CollectionHandler init max_items=%s concurrency=%s per_item_retries=%s progress_interval=%s",
            self._max_items,
            eff_concurrency,
            eff_retries,
            eff_progress_sec,
        )                                                                 # 🧾 Фіксуємо конфіг DI

    # ==========================
    # ▶️ ПУБЛІЧНИЙ МЕТОД
    # ==========================
    async def handle_collection(self, update: Update, context: CustomContext, url: Optional[str] = None) -> None:
        """
        Приймає посилання на колекцію, запускає обробку та показує прогрес.
        """
        progress_msg: Optional[Message] = None								# 💬 Повідомлення, яке оновлюємо під час прогресу
        can_edit_progress = True										# 🛡️ Після першої помилки редагування — більше не пробуємо
        user_id: str = "unknown"										# 🆔 Ініціалізація для логів (перед guard)
        effective_url: str = ""										# 🔗 Початковий URL (може не бути заданий)

        try:
            raw_url = url or context.url
            if not update.message or not raw_url:
                logger.debug("📭 Skip collection handling (message=%s url=%s)", bool(update.message), bool(context.url))
                return											# 🚪 Нема що обробляти (unsafe guard)

            effective_url = raw_url.strip()									# ✂️ Нормалізуємо URL
            context.url = effective_url										# 🧷 Зберігаємо normalized URL у контексті
            user_id = getattr(update.effective_user, "id", "unknown")                     # 🆔 Ідентифікатор користувача
            logger.info("🗂️ Collection requested user=%s url=%s", user_id, effective_url)  # 🧾 Фіксуємо запит

            # ==========================
            # ✅ ВАЛІДАЦІЯ URL
            # ==========================
            try:
                # Якщо в сервісі є is_valid_url — використовуємо його
                is_valid = self._url_parser.is_valid_url(effective_url)  # type: ignore[attr-defined]
            except Exception:
                # Фолбек — простий префікс
                is_valid = effective_url.startswith(("http://", "https://"))

            if not is_valid:
                logger.warning("⚠️ Invalid collection URL user=%s url=%s", user_id, effective_url)
                await update.message.reply_text(msg.COLL_INVALID_URL)
                return											# 🧱 Зупиняємось — лінк невалідний

            await update.message.reply_text(msg.COLL_START)						# ▶️ Запуск: службове повідомлення
            logger.info("▶️ Collection processing started user=%s", user_id)

            # ==========================
            # 🌍 РЕГІОН + ПЕРШЕ ПОВІДОМЛЕННЯ ПРОГРЕСУ
            # ==========================
            region_display = self._url_parser.get_region_label(effective_url)		# 🌍 Обчислюємо регіон для UI
            parse_mode = getattr(
                getattr(self._const, "UI", object()), "DEFAULT_PARSE_MODE", None
            )												# 🧩 Опційний parse_mode (Markdown/HTML)
            progress_msg = await update.message.reply_text(
                msg.COLL_REGION.format(region=region_display),
                parse_mode=parse_mode,
            )											# 💬 Перше повідомлення прогресу (буде редагуватись далі)
            logger.info("🌍 Collection region=%s user=%s", region_display, user_id)

            # ==========================
            # 🔗 ЗБІР ПОСИЛАНЬ (з ретраями)
            # ==========================
            urls = await self._get_links_with_retry(effective_url)				# 🧵 Отримуємо всі посилання на товари
            if not urls:
                logger.info("📭 Collection empty user=%s url=%s", user_id, effective_url)
                if progress_msg and can_edit_progress:
                    with contextlib.suppress(Exception):
                        await progress_msg.edit_text(msg.COLL_EMPTY)			# 🔕 Нічого не знайшли — інформуємо
                return

            # Ліміт на кількість
            if self._max_items and len(urls) > self._max_items:
                logger.warning("✂️ Collection trimmed user=%s count=%s max=%s", user_id, len(urls), self._max_items)
                await update.message.reply_text(
                    msg.COLL_TOO_LARGE.format(max=self._max_items)
                )
                urls = urls[: self._max_items]								# ✂️ Обрізаємо зайві URL за лімітом

            if progress_msg and can_edit_progress:
                with contextlib.suppress(Exception):
                    await progress_msg.edit_text(
                        msg.COLL_FOUND.format(count=len(urls))
                    )											# 🔢 Показуємо скільки посилань зібрали

            # ==========================
            # 🔗 КОЛБЕКИ ДЛЯ RUNNER
            # ==========================
            modes = getattr(getattr(self._const, "LOGIC", object()), "MODES", object())
            collection_mode_value = getattr(modes, "COLLECTION", "collection")	# 🔖 Значення режиму "колекція" у контексті

            def _is_cancelled() -> bool:
                return getattr(context, "mode", None) != collection_mode_value	# 🛑 Якщо юзер змінив режим — зупиняємося

            async def _on_progress(snapshot: CollectionProgressSnapshot) -> None:
                nonlocal can_edit_progress
                if progress_msg and can_edit_progress:
                    try:
                        await progress_msg.edit_text(
                            self._build_progress_text(snapshot),
                            parse_mode=parse_mode,
                        )
                    except Exception:
                        can_edit_progress = False

            # ==========================
            # ▶️ ЗАПУСК RUNNER
            # ==========================
            logger.info("🚀 Collection runner start user=%s total_urls=%s", user_id, len(urls))
            done_count, health_summary = await self._runner.run(
                update, context, urls, _on_progress, _is_cancelled
            )												# 🚀 Паралельна обробка посилань з колекції

            logger.info("🏁 Collection finished user=%s processed=%s", user_id, done_count)
            logger.info(
                "🩺 Collection health: total=%d ok=%d alt_fallback=%d failed=%d",
                health_summary.total,
                health_summary.ok,
                health_summary.alt_fallback,
                health_summary.failed,
            )
            if health_summary.total:
                summary_text = msg.COLL_HEALTH_SUMMARY.format(
                    ok=health_summary.ok,
                    alt_fallback=health_summary.alt_fallback,
                    failed=health_summary.failed,
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=summary_text,
                    parse_mode=parse_mode,
                )

        except asyncio.CancelledError:
            logger.info("🛑 Collection handling cancelled user=%s", user_id)
            if progress_msg:
                with contextlib.suppress(Exception):
                    await progress_msg.edit_text(msg.COLL_CANCELLED)			# 🪫 Повідомляємо про скасування
            return
        except Exception as exc:
            await self._exception_handler.handle(exc, update)				# 🧯 Центральна обробка помилок
            logger.exception("🔥 Collection handling failed user=%s url=%s", user_id, effective_url)

    # ==========================
    # 🧱 ФОРМАТУВАННЯ ПРОГРЕСУ
    # ==========================
    def _build_progress_text(self, snapshot: CollectionProgressSnapshot) -> str:
        header = msg.COLL_PROGRESS.format(processed=snapshot.completed, total=snapshot.total)
        lines: list[str] = [header, ""]
        for status in snapshot.statuses:
            lines.append(self._format_status_line(status))
        if snapshot.completed >= snapshot.total and snapshot.total:
            lines.append("")
            lines.append(msg.COLL_DONE_STATUS.format(success=snapshot.successes, total=snapshot.total))
        return "\n".join(line for line in lines if line is not None)

    def _format_status_line(self, status: CollectionItemStatus) -> str:
        icon = self._STATUS_ICONS.get(status.state, "⚪️")
        detail = self._trim_detail(status.detail)
        suffix = f" — {detail}" if detail else ""
        name = status.display_name()
        return f"{icon} {name}{suffix}"

    @staticmethod
    def _trim_detail(detail: Optional[str], limit: int = 80) -> str:
        if not detail:
            return ""
        cleaned = " ".join(detail.strip().split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1] + "…"

    # ==========================
    # 🔧 ДОПОМІЖНІ
    # ==========================
    async def _get_links_with_retry(self, url: str, attempts: int = 3) -> List[str]:
        """
        Отримує посилання з колекції з повторними спробами та дедуплікацією.
        """
        delay = 0.8											# ⏱️ Базова пауза між спробами
        for attempt in range(attempts):
            try:
                links = await self._proc_service.get_product_links(url)			# 🌐 Запит усіх посилань із сторінки колекції
                seen: set[str] = set()									# 🧺 Для дедуплікації
                out: List[str] = []
                for link_obj in links or []:
                    link_value: str
                    if isinstance(link_obj, Url):
                        link_value = link_obj.value
                    else:
                        link_value = str(link_obj).strip()

                    if not link_value or link_value in seen:
                        continue									# 🧹 Пропускаємо пусті/дублікати
                    seen.add(link_value)
                    out.append(link_value)
                logger.info("🔗 Collected %s links from %s", len(out), url)
                return out										# ✅ Повертаємо чистий список
            except Exception as exc:
                logger.warning(
                    "Спроба %s/%s отримати посилання з колекції невдала: %s",
                    attempt + 1,
                    attempts,
                    exc,
                )											# ⚠️ Лог попередження з номером спроби
                if attempt == attempts - 1:
                    logger.error("❌ Вичерпано спроби отримати посилання для %s", url)
                    raise									# ❌ Вичерпали спроби — пробрасываемо виняток
                await asyncio.sleep(delay)								# ⏳ Чекаємо перед наступною спробою
                delay *= 2										# 📈 Експоненційний бекоф
        return []												# 🕳️ На крайній випадок повертаємо пустий список
