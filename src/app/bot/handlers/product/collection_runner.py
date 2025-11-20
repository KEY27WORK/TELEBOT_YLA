# 🏃 app/bot/handlers/product/collection_runner.py
"""
🏃 CollectionRunner — керує паралельною обробкою товарів з колекції.

🔹 Можливості:
    • Обмежує паралелізм через семафор (керований рівень concurrency)
    • Ретраї з експоненційною затримкою для кожного товару (exponential backoff)
    • Троттлить оновлення прогресу, щоб не заспамити UI-редагуваннями
    • Акуратно завершує задачі при `CancelledError` (graceful cancellation)
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update                                             # 📬 Telegram Update (використовується у handler)

# 🔠 Системні імпорти
import asyncio                                                          # 🔄 Асинхронність / таски / семафори
import contextlib                                                       # 🧰 Безпечне подавлення винятків
import logging                                                          # 🧾 Логування подій
import time                                                             # ⏱️ Вимірювання часу для тротлінгу
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, List, Optional, Sequence, Tuple

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.product_handler import (                  # 🛍️ Обробник одного товару (UI‑шар)
    PreparedProductCard,
    ProductHandler,
)
from app.bot.services.custom_context import CustomContext               # 🧠 Розширений контекст бота
from app.infrastructure.services.collection_health import CollectionHealthSummary  # 🩺 Звіти про здоров'я колекції
from app.shared.utils.logger import LOG_NAME                            # 🏷️ Ім'я логера з єдиного централізованого місця


# ==========================
# 🧾 ЛОГЕР
# ==========================
logger = logging.getLogger(LOG_NAME)


class CollectionItemState(str, Enum):
    """Стан окремого товару в рамках колекції."""

    PENDING = "pending"
    PROCESSING = "processing"
    RETRYING = "retry"
    OK = "ok"
    FAILED = "failed"


@dataclass(slots=True)
class CollectionItemStatus:
    """Відображає прогрес обробки одного URL."""

    index: int
    url: str
    title: str = ""
    state: CollectionItemState = CollectionItemState.PENDING
    detail: Optional[str] = None

    def display_name(self) -> str:
        return self.title or f"#{self.index + 1}"


@dataclass(slots=True)
class CollectionProgressSnapshot:
    """Знімок загального прогресу колекції."""

    completed: int
    total: int
    successes: int
    statuses: Tuple[CollectionItemStatus, ...]


# ==========================
# 🏛️ КЛАС RUNNER
# ==========================
class CollectionRunner:
    """
    🏃 Запускає обробку товарів з обмеженням паралелізму, ретраями та тротлінгом прогресу.
    """

    def __init__(
        self,
        product_handler: ProductHandler,
        concurrency: int = 4,
        per_item_retries: int = 2,
        progress_interval_sec: float = 2.5,
    ) -> None:
        """
        ⚙️ Ініціалізує Runner необхідними залежностями та політиками виконання.

        Args:
            product_handler: Обробник одного товару (UI‑шар), який уміє опрацьовувати URL.
            concurrency: Скільки товарів обробляємо одночасно (розмір семафора).
            per_item_retries: Кількість повторних спроб на один URL (включно з першою спробою + N ретраїв).
            progress_interval_sec: Мінімальний інтервал між оновленнями прогресу (сек).
        """
        self._product_handler = product_handler								# 🛍️ Зберігаємо посилання на UI‑обробник товару
        self._sem = asyncio.Semaphore(concurrency)							# 🚦 Семафор лімітує кількість одночасних задач
        self._retries = per_item_retries									# 🔁 Політика кількості ретраїв на товар
        self._progress_interval = progress_interval_sec						# ⏱️ Мінімальний інтервал пушів прогресу

    # ==========================
    # ▶️ ПУБЛІЧНИЙ МЕТОД
    # ==========================
    async def run(
        self,
        update: Update,
        context: CustomContext,
        urls: List[str],
        on_progress: Callable[[CollectionProgressSnapshot], Awaitable[None]],
        is_cancelled: Callable[[], bool],
    ) -> tuple[int, CollectionHealthSummary]:
        """
        ▶️ Запускає обробку списку URL з контролем паралелізму, ретраїв і тротлінгу.

        Returns:
            tuple[int, CollectionHealthSummary]: (успішно відправлено, health-звіт).
        """
        success_count = 0                                               # 🔢 Лічильник успішно надісланих карточок
        completed_count = 0                                             # 🔢 Скільки товарів уже завершено (успіх + фейл)
        total = len(urls)                                               # 📦 Загальна кількість
        last_push_time = 0.0                                            # 🕓 Останній час оновлення прогресу
        health = CollectionHealthSummary()                              # 🩺 Метрики стану колекції
        statuses: List[CollectionItemStatus] = [
            CollectionItemStatus(index=i, url=url) for i, url in enumerate(urls)
        ]
        status_lock = asyncio.Lock()

        def _resolve_title(card: Optional[PreparedProductCard], idx: int) -> str:
            data = getattr(card.result, "data", None) if card else None
            title = getattr(getattr(data, "content", object()), "title", "") if data else ""
            return title or f"#{idx + 1}"

        async def _push_progress(force: bool = False) -> None:
            nonlocal last_push_time
            now = time.monotonic()
            if not force and completed_count < total and (now - last_push_time) < self._progress_interval:
                return
            last_push_time = now
            async with status_lock:
                snapshot_statuses = tuple(
                    CollectionItemStatus(
                        index=s.index,
                        url=s.url,
                        title=s.title,
                        state=s.state,
                        detail=s.detail,
                    )
                    for s in statuses
                )
            try:
                await on_progress(
                    CollectionProgressSnapshot(
                        completed=completed_count,
                        total=total,
                        successes=success_count,
                        statuses=snapshot_statuses,
                    )
                )
            except Exception:  # noqa: BLE001
                pass

        async def _update_status(
            idx: int,
            state: CollectionItemState,
            *,
            detail: Optional[str] = None,
            title: Optional[str] = None,
            force: bool = False,
        ) -> None:
            async with status_lock:
                current = statuses[idx]
                if title:
                    current.title = title
                current.state = state
                current.detail = detail
            if force:
                await _push_progress(force=True)

        async def _process_one_url(idx: int, url: str) -> Tuple[int, Optional[PreparedProductCard]]:
            if is_cancelled():
                await _update_status(idx, CollectionItemState.FAILED, detail="Скасовано", force=True)
                return idx, None

            async with self._sem:
                delay = 0.6
                for attempt in range(self._retries + 1):
                    try:
                        await _update_status(idx, CollectionItemState.PROCESSING)
                        prepared = await self._product_handler.handle_url(
                            update,
                            context,
                            url=url,
                            update_currency=False,
                            send_immediately=False,
                        )
                        return idx, prepared
                    except asyncio.CancelledError:
                        logger.info("🛑 Cancelled item: %s", url)
                        await _update_status(idx, CollectionItemState.FAILED, detail="Скасовано", force=True)
                        return idx, None
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "[CollectionRunner] Помилка (%s/%s) на %s: %s",
                            attempt + 1,
                            self._retries + 1,
                            url,
                            exc,
                        )
                        await _update_status(
                            idx,
                            CollectionItemState.RETRYING,
                            detail=str(exc),
                            force=True,
                        )
                        if attempt >= self._retries:
                            return idx, None
                        await asyncio.sleep(delay)
                        delay *= 2

            return idx, None

        tasks = [asyncio.create_task(_process_one_url(i, url)) for i, url in enumerate(urls)]
        await _push_progress(force=True)

        try:
            for fut in asyncio.as_completed(tasks):
                idx, prepared_card = await fut
                completed_count += 1

                if prepared_card and prepared_card.result.ok and prepared_card.media_stack:
                    data = prepared_card.result.data
                    if not data:
                        health.register_failed()
                        await _update_status(
                            idx,
                            CollectionItemState.FAILED,
                            detail="Порожні дані картки",
                            force=True,
                        )
                    else:
                        try:
                            await self._product_handler.send_prepared_card(
                                update,
                                context,
                                prepared_card,
                                include_region_notice=False,
                            )
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Не вдалося надіслати картку %s: %s", data.url, exc)
                            health.register_failed()
                            await _update_status(
                                idx,
                                CollectionItemState.FAILED,
                                detail=str(exc),
                                title=data.content.title,
                                force=True,
                            )
                        else:
                            success_count += 1
                            health.register_ok(prepared_card.result.alt_fallback_used)
                            await _update_status(
                                idx,
                                CollectionItemState.OK,
                                title=data.content.title,
                                detail=None,
                                force=True,
                            )
                else:
                    health.register_failed()
                    reason = ""
                    if prepared_card and prepared_card.result.error_message:
                        reason = prepared_card.result.error_message
                    await _update_status(
                        idx,
                        CollectionItemState.FAILED,
                        detail=reason or "Не вдалося обробити товар",
                        title=_resolve_title(prepared_card, idx),
                        force=True,
                    )

                await _push_progress(force=False)

        except asyncio.CancelledError:
            logger.info("🛑 CollectionRunner cancelled")
            for task in tasks:
                task.cancel()
        finally:
            with contextlib.suppress(Exception):
                await asyncio.gather(*tasks, return_exceptions=True)

        return success_count, health
 
