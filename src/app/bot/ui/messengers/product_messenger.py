# 📬 app/bot/ui/messengers/product_messenger.py
"""
📬 Координує відправку всіх UI-блоків товару у Telegram.

🔹 Відправляє текстовий опис, заголовок і прайс-звіт у правильній послідовності
🔹 Додає додаткові блоки (музика, фото/альбоми, таблиці розмірів)
🔹 Делегує бізнес-логіку допоміжним сервісам, концентруючись на оркестрації UI
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update                                              # 🤖 Telegram Bot API (type stubs можуть бути відсутні)

# 🔠 Системні імпорти
import asyncio                                                           # ⏱️ Асинхронні паузи між блоками
import logging                                                           # 🧾 Логування перебігу сценарію
import re                                                                # 🔍 Нормалізація музичних рекомендацій
from typing import Final, Optional, Sequence                           # 🧰 Типи для медіастеку

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.image_sender import (                     # 🖼️ Відправка фотографій/альбомів
    ImageSender,
    MediaRef,
)
from app.bot.handlers.size_chart_handler_bot import SizeChartHandlerBot  # 📏 Надсилання таблиць розмірів
from app.bot.services.custom_context import CustomContext                # 🧰 Розширений контекст бота
from app.bot.ui import static_messages as msg                            # 📝 Статичні повідомлення UI
from app.config.setup.constants import AppConstants                      # ⚙️ Глобальні константи застосунку
from app.errors.exception_handler_service import ExceptionHandlerService # 🛡️ Централізована обробка винятків
from app.infrastructure.music.music_sender import MusicSender            # 🎵 Надсилання музичних рекомендацій
from app.infrastructure.services.product_processing_service import (
    ProcessedProductData,                                                # 📦 Агрегований результат обробки товару
)
from app.shared.utils.logger import LOG_NAME                             # 🏷️ Ім'я кореневого логера
from ..formatters.message_formatter import MessageFormatter              # 🧩 Форматування текстових блоків

# ================================
# 🧾 ЛОГЕР ТА КОНСТАНТИ МОДУЛЯ
# ================================
logger: Final = logging.getLogger(LOG_NAME)                              # 🧾 Модульний логер
_BLOCK_PAUSE_SEC: Final[float] = 0.10                                    # ⏳ Паузи між блоками для уникнення rate-limit


# ================================
# 🏛️ КООРДИНАТОР ВІДПРАВКИ ТОВАРУ
# ================================
class ProductMessenger:
    """
    🧭 Оркеструє послідовну доставку усіх UI-блоків товару.

    Приймає вже підготовлений контент і делегує відправку спеціалізованим сервісам.
    """

    def __init__(
        self,
        music_sender: MusicSender,
        size_chart_handler: SizeChartHandlerBot,
        formatter: MessageFormatter,
        image_sender: ImageSender,
        exception_handler: ExceptionHandlerService,
        constants: AppConstants,
    ) -> None:
        self.music_sender = music_sender                                  # 🎵 DI: сервіс відправки музики
        self.size_chart_handler = size_chart_handler                      # 📏 DI: побудова та надсилання size-chart
        self.formatter = formatter                                        # 🧩 DI: форматування текстових блоків
        self.image_sender = image_sender                                  # 🖼️ DI: надсилання фото/альбомів
        self.exception_handler = exception_handler                        # 🛡️ DI: централізована обробка винятків
        self.const = constants                                            # ⚙️ DI: глобальні константи (parse_mode тощо)

    # ================================
    # 📤 ОСНОВНИЙ МЕТОД ВІДПРАВКИ
    # ================================
    async def send(
        self,
        update: Update,
        context: CustomContext,
        data: ProcessedProductData,
        *,
        media_stack: Optional[Sequence[MediaRef]] = None,
    ) -> None:
        """
        🚚 Відправляє опис, заголовок, прайс, музику, фото та таблицю розмірів.
        """
        try:
            if update.message is None:                                    # 🚫 Callback без повідомлення → нічого надсилати
                return                                                   # 🛑 Завершуємо сценарій

            chat_id = getattr(update.effective_chat, "id", None)          # 🆔 Chat ID для діагностики
            user_id = getattr(update.effective_user, "id", None)          # 👤 User ID для аудиту

            title_upper = data.content.title.upper()                      # 🔠 Назва товару капсом (визуальний акцент)
            description_text = self.formatter.format_description(         # 🧩 Форматуємо опис
                data.content,
            )
            parse_mode = self.const.UI.DEFAULT_PARSE_MODE                 # 🅿️ Режим розмітки (HTML/Markdown)

            await update.message.reply_text(                              # 📨 Основний опис товару
                description_text,
                parse_mode=parse_mode,
            )
            await asyncio.sleep(_BLOCK_PAUSE_SEC)                         # ⏳ Пауза, щоб не впертись у rate-limit

            await update.message.reply_text(                              # 🏷️ Назва товару капсом
                f"<b>{title_upper}</b>",
                parse_mode=parse_mode,
            )
            await asyncio.sleep(_BLOCK_PAUSE_SEC)                         # ⏳ Коротка пауза перед наступним блоком

            await update.message.reply_text(                              # 💵 Прайс-звіт
                data.content.price_message,
                parse_mode=parse_mode,
            )

            logger.info(                                                  # 🧾 Фіксуємо успішну відправку основних блоків
                "📨 Текстові блоки відправлено | chat_id=%s user_id=%s title=%s",
                chat_id,
                user_id,
                title_upper,
            )

            await self._send_music_block(update, context, data.music_text, title_upper)  # 🎵 Музичні рекомендації

            final_media = media_stack if media_stack is not None else data.content.images
            if not final_media:
                logger.warning("🖼️ Стек фото порожній | title=%s", title_upper)
                return

            sent_media = await self.image_sender.send_images(             # 🖼️ Фото/альбоми товару
                update=update,
                context=context,
                images=final_media,
            ) or []                                                       # 🔁 Гарантуємо список навіть у разі None
            logger.info(                                                  # 🧾 Лог відправлених фото
                "🖼️ Фото відправлено | chat_id=%s user_id=%s requested=%d sent=%d",
                chat_id,
                user_id,
                len(data.content.images),
                len(sent_media),
            )

            await self.size_chart_handler.size_chart_command(             # 📏 Таблиця розмірів (використовує кешовані HTML)
                update=update,
                context=context,
                url=data.url,                                             # 🔗 Посилання на товар
                page_source=data.page_source,                             # 📄 HTML сторінки (щоб не вантажити повторно)
            )
            logger.info(                                                  # 🧾 Лог успішного надсилання size-chart
                "📏 Таблиця розмірів відправлена | chat_id=%s user_id=%s title=%s",
                chat_id,
                user_id,
                title_upper,
            )

        except asyncio.CancelledError:
            raise                                                         # 🔁 Проброс скасування (важливо для asyncio)
        except Exception as error:  # noqa: BLE001
            await self.exception_handler.handle(error, update)            # 🛡️ Делегуємо обробку винятку

    # ================================
    # 🎵 ДОПОМІЖНИЙ БЛОК МУЗИКИ
    # ================================
    async def _send_music_block(
        self,
        update: Update,
        context: CustomContext,
        music_text: str,
        title: str,
    ) -> None:
        """
        🎶 Відправляє музичні рекомендації, якщо вони присутні.
        """
        if update.message is None:                                        # 🚫 Без повідомлення не можемо відповісти
            return                                                       # 🛑 Завершуємо блок
        if not music_text:                                                # ℹ️ Музика не згенерована — просто лог/вихід
            logger.warning("🎵 Музика не згенерована | title=%s", title)
            return

        try:
            track_names = self._parse_track_names(music_text)             # 🧩 Нормалізуємо «сирий» список треків
            if not track_names:                                           # 🟡 Після парсингу треків немає
                logger.warning("🎵 Порожній список треків після парсингу | title=%s", title)
                return

            await self.music_sender.send_recommendations_legacy(          # 🚀 Відправляємо рекомендації
                update,
                context,
                track_names,
            )
            logger.info("🎵 Музика відправлена | title=%s tracks=%d", title, len(track_names))  # 🧾 Лог успіху

        except asyncio.CancelledError:
            raise                                                         # 🔁 Проброс скасування
        except Exception as error:  # noqa: BLE001
            logger.warning("🎵 Помилка відправки музики: %s | title=%s", error, title)  # ⚠️ Діагностика
            await update.message.reply_text(msg.MUSIC_SEND_ERROR)         # 📤 Пояснюємо користувачу збій

    # ================================
    # 🔎 ДОПОМІЖНИЙ ПАРСЕР ТРЕКІВ
    # ================================
    def _parse_track_names(self, text: str) -> list[str]:
        """
        Витягує назви треків із «сирого» тексту (можлива нумерація або буліти).
        """
        raw_lines = (text or "").splitlines()                             # 🧾 Первинні рядки (можуть бути порожні)
        trimmed_lines = [ln.strip() for ln in raw_lines]                  # ✂️ Прибираємо зайві пробіли
        filtered_lines = [                                                # 🧹 Відкидаємо технічні заголовки/порожні рядки
            ln
            for ln in trimmed_lines
            if ln
            and not ln.lower().startswith(("музика", "music", "tracks", "рекомендації"))
        ]

        cleaned: list[str] = []                                           # 📦 Кінцевий список треків
        for candidate in filtered_lines:                                  # 🔁 Обробляємо кожен рядок
            without_prefix = re.sub(r"^\s*(?:\d+[\.\)]\s+|[-–—•]\s+)", "", candidate)  # 🧽 Прибираємо нумерацію/буліти
            normalized = re.sub(r"\s{2,}", " ", without_prefix).strip()   # 🧴 Нормалізуємо повторні пробіли
            if normalized:                                                # ✅ Додаємо, якщо залишився вміст
                cleaned.append(normalized)

        return cleaned                                                    # 📤 Повертаємо перелік назв треків
