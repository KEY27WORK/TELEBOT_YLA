# 🖼️ app/bot/handlers/product/image_sender.py
"""
🖼️ image_sender.py — Сервіс надсилання зображень у Telegram (single / media group) з backoff‑ретраями.

🔹 Підтримує URL, file_id та InputFile.
🔹 Враховує ліміти Telegram: 1 → photo, 2..10 → media group, >10 → надсилання чанками по 10.
🔹 Безпечно працює при відсутності update.message (fallback через context.bot).
🔹 Не передає None у PTB v21 (жодних reportArgumentType / OptionalMemberAccess).
🔹 Централізовано делегує помилки в ExceptionHandlerService.
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update, Message, InputMediaPhoto, InputFile                         # 📦 Telegram-типи
from telegram.constants import ChatAction                                               # 🪄 Індикація "друкує / завантажує фото"
from telegram.error import BadRequest, RetryAfter, NetworkError                         # 🚨 Типи помилок Telegram

# 🔠 Системні імпорти
from typing import Optional, Sequence, TypeAlias, Union, List, Dict, Any                # 🧰 Типізація
import asyncio                                                                          # ⏱️ Асинхронні затримки / sleep
import logging                                                                          # 🧾 Логування
import random                                                                           # 🎲 Джиттер для backoff

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext                               # 🧠 Наш розширений контекст PTB
from app.bot.ui import static_messages as msg                                           # 💬 Статичні повідомлення UI
from app.config.setup.constants import AppConstants                                     # ⚙️ Константи застосунку
from app.errors.exception_handler_service import ExceptionHandlerService                # 🧯 Єдиний хендлер винятків
from app.shared.utils.logger import LOG_NAME                                            # 🏷️ Ім'я логера

# ==============================
# 🧾 ЛОГЕР
# ==============================
logger = logging.getLogger(LOG_NAME)                                                    # 🏷️ Створюємо модульний логер

# ==============================
# 🏷️ Типи та константи
# ==============================
MediaRef = Union[str, InputFile]         # url | file_id | InputFile                                         			# 🧩 Дозволені типи для фото
Urls: TypeAlias = Sequence[MediaRef]     # Послідовність медіа-референсів                                   			# 🧾 Алiас для списку вхідних зображень

_MAX_MEDIA_PER_GROUP = 10                # елементів у media group                                         			# 🔢 Telegram дозволяє максимум 10
_MAX_RETRIES = 3                         # скільки разів ретраїм 429                                        			# 🔁 Обмежуємо кількість повторів
_BASE_DELAY_SEC = 1.0                    # базова затримка для експоненційного backoff                     			# ⏱️ Початковий інтервал
_DEFAULT_BATCH_PAUSE_SEC = 0.4           # пауза між батчами (щоб не дзвонити в rate limit)                			# 🧘 Кулдаун між групами

# ==============================
# 🏛️ СЕРВІС ВІДПРАВКИ ЗОБРАЖЕНЬ
# ==============================
class ImageSender:
    """
    📦 Сервіс для надсилання зображень (по одному або альбомами) з урахуванням обмежень Telegram.
    Повертає список відправлених повідомлень (`telegram.Message`) для подальших дій (редагування/видалення).
    """

    def __init__(self, exception_handler: ExceptionHandlerService, constants: AppConstants) -> None:
        self.exception_handler = exception_handler                                    			# 🧯 Централізована обробка помилок
        self.const = constants                                                        			# ⚙️ Доступ до констант (UI/SENDING тощо)

    # ==============================
    # 🔄 ПУБЛІЧНИЙ ІНТЕРФЕЙС
    # ==============================
    async def send_images(
        self,
        update: Update,
        context: CustomContext,
        images: Urls,
        *,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
    ) -> List[Message]:
        """
        🚀 Надсилає список зображень. Автовибір режиму: одиночне фото або media group (чанки по 10).
        Повертає список `Message` (може бути порожнім, якщо немає валідних зображень).
        """
        sent: List[Message] = []                                                      			# 📥 Акумулюємо відправлені повідомлення
        try:
            unique_media = self._normalize_media(images)                              			# 🧹 Прибираємо None/дублі, зберігаємо порядок
            if not unique_media:
                await self._send_text_safe(update, context, msg.IMAGES_NOT_FOUND)     			# 💬 Акуратний фолбек у чат
                logger.warning("⚠️ Порожній список зображень — нічого відправляти.")
                return sent

            # 👋 Спроба показати індикацію "завантажує фото" (не критично, тому в try/except)
            try:
                if update.message and update.message.chat:
                    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)     			# 🪄 Індикація для чату з message
                elif update.effective_chat:
                    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)  # 🪄 Індикація fallback
            except Exception:
                pass                                                                    			# 🔇 Не шумимо, це лише косметика

            # 📝 Визначаємо parse_mode за замовчуванням з констант (якщо не передано вручну)
            default_parse_mode = getattr(getattr(self.const, "UI", object()), "DEFAULT_PARSE_MODE", None)  # 🔎 Може бути None — це ок
            final_parse_mode = parse_mode or default_parse_mode                                 			# ✅ Бере користувацький або дефолтний

            # ✂️ Якщо підпис занадто довгий — відправляємо окремим повідомленням перед фото(ами)
            if self._should_detach_caption(caption):
                await self._send_text_safe(update, context, caption, parse_mode=final_parse_mode) 			# 💬 Спочатку текст
                caption = None                                                                           	# 🧼 Потім фото без підпису

            total = len(unique_media)                                                       			# 🔢 Скільки всього фото?
            if total == 1:
                m = await self._send_single_photo(                                           			# 🖼️ Режим одиночного фото
                    update, context, unique_media[0],
                    caption=caption, parse_mode=final_parse_mode,
                    reply_to_message_id=reply_to_message_id,
                    disable_notification=disable_notification, protect_content=protect_content,
                )
                if m: sent.append(m)                                                        			# ✅ Додаємо, якщо успішно
                return sent

            # 🧱 Батуємо у групи по 10 елементів
            total_batches = (total + _MAX_MEDIA_PER_GROUP - 1) // _MAX_MEDIA_PER_GROUP                	# 🧮 Скільки батчів
            batch_pause = float(getattr(getattr(self.const, "SENDING", object()), "BATCH_PAUSE_SEC", _DEFAULT_BATCH_PAUSE_SEC))  # 🧘 Пауза між батчами

            for i in range(0, total, _MAX_MEDIA_PER_GROUP):
                chunk = list(unique_media[i : i + _MAX_MEDIA_PER_GROUP])                    			# ✂️ Беремо шматок до 10
                first_caption = caption if i == 0 else None                                  			# 🏷️ Підпис лише на першому елементі групи

                batch_msgs = await self._send_media_group_chunk(                             			# 📦 Відправляємо батч
                    update, context, chunk,
                    first_caption=first_caption, parse_mode=final_parse_mode,
                    reply_to_message_id=reply_to_message_id if i == 0 else None,            			# 🔗 reply — лише на першій групі
                    disable_notification=disable_notification, protect_content=protect_content,
                    batch_index=i // _MAX_MEDIA_PER_GROUP + 1, total_batches=total_batches,
                )
                sent.extend(batch_msgs)                                                     			# ➕ Акумулюємо повідомлення
                await asyncio.sleep(batch_pause)                                            			# 🧘 Трохи відпочиваємо, аби не ввалитися в rate limit

        except Exception as e:
            await self.exception_handler.handle(e, update)                                  			# 🧯 Централізований репорт та user-friendly фолбек

        return sent                                                                         			# 📤 Повертаємо список повідомлень

    # ==============================
    # 🔧 Приватні допоміжні
    # ==============================
    @staticmethod
    def _normalize_media(items: Urls) -> List[MediaRef]:
        """
        🧹 Повертає список без порожніх значень та дублікатів. Підтримує `str` (url/file_id) і `InputFile`.
        Порядок зберігається.
        """
        out: List[MediaRef] = []                                                            			# 📦 Акумулятор
        seen: set[str] = set()                                                              			# 👀 Для унікальності лише рядкових значень
        for it in items or []:
            if it is None:                                                                   			# 🚫 Пропускаємо пусті
                continue
            if isinstance(it, InputFile):
                out.append(it)                                                               			# 🧾 InputFile не дедупимо: вміст може відрізнятись
                continue
            if isinstance(it, str):
                s = it.strip()                                                               			# ✂️ Зрізаємо пробіли
                if not s or s in seen:                                                       			# 🚫 Порожнє або дубль — скіпаємо
                    continue
                seen.add(s)                                                                  			# ✅ Запам'ятали
                out.append(s)
        return out

    @staticmethod
    def _should_detach_caption(caption: Optional[str]) -> bool:
        """📝 Від'єднати підпис, якщо він довший за ~900 символів (безпечніше для media group)."""
        return bool(caption and len(caption) > 900)                                         			# 📏 Просте евристичне правило

    @staticmethod
    def _kv_if_set(key: str, value: Optional[Any]) -> Dict[str, Any]:
        """
        🛡️ Будує kwargs без передачі None, щоб уникнути помилок типізації/PTB v21.
        """
        return {} if value is None else {key: value}                                        			# ✅ Лише встановлені значення

    async def _retry_sleep(self, retry_after: Optional[float], attempt: int) -> None:
        """
        ⏳ Затримка між спробами: експоненційний backoff з невеликим джиттером.
        """
        if retry_after:
            await asyncio.sleep(float(retry_after))                                        			# ⏱️ Поважаємо вказаний Telegram час
            return
        delay = _BASE_DELAY_SEC * (2 ** attempt) + random.uniform(0, 0.25)                 			# 📈 Експонента + 🎲 джиттер
        await asyncio.sleep(delay)                                                          			# 💤 Спимо перед повтором
        
    async def _send_text_safe(
        self,
        update: Update,
        context: CustomContext,
        text: Optional[str],
        *,
        parse_mode: Optional[str] = None,
    ) -> Optional[Message]:
        """
        💬 Безпечно надсилає текст: через reply_text (якщо є message) або через bot.send_message (fallback).
        Не кидає винятків назовні.
        """
        if not text:                                                                        			# 🛡️ Захист від None/порожніх рядків
            return None

        try:
            if update.message:
                return await update.message.reply_text(text=text, parse_mode=parse_mode)    			# ✉️ Відповідь на вихідне повідомлення
            if update.effective_chat:
                return await context.bot.send_message(                                      			# 📮 Відправка напряму в чат
                    chat_id=update.effective_chat.id,
                    text=text,
                    parse_mode=parse_mode,
                )
        except Exception as e:
            logger.warning("⚠️ Не вдалося відправити текстове повідомлення: %s", e)         			# 📝 Не фейлимо увесь флоу

        return None

    # ==============================
    # 🖼️ ОДИНАРНЕ ФОТО
    # ==============================
    async def _send_single_photo(
        self,
        update: Update,
        context: CustomContext,
        photo: MediaRef,
        *,
        caption: Optional[str],
        parse_mode: Optional[str],
        reply_to_message_id: Optional[int],
        disable_notification: Optional[bool],
        protect_content: Optional[bool],
    ) -> Optional[Message]:
        """
        🎯 Універсальна відправка одного фото з ретраями та без передачі None у PTB.
        """
        chat_id = update.effective_chat.id if update.effective_chat else None             			# 🆔 Куди слати, якщо немає message
        has_message = bool(update.message)                                                			# 📩 Є початкове повідомлення?

        kwargs: Dict[str, Any] = {}                                                       			# 🧱 Збираємо лише валідні kwargs
        kwargs.update(self._kv_if_set("caption", caption))
        kwargs.update(self._kv_if_set("parse_mode", parse_mode))
        kwargs.update(self._kv_if_set("reply_to_message_id", reply_to_message_id))
        kwargs.update(self._kv_if_set("disable_notification", disable_notification))
        kwargs.update(self._kv_if_set("protect_content", protect_content))

        for attempt in range(_MAX_RETRIES):
            try:
                if has_message and update.message:
                    return await update.message.reply_photo(photo=photo, **kwargs)         			# 🖼️ Надсилання як reply
                if chat_id is not None:
                    return await context.bot.send_photo(chat_id=chat_id, photo=photo, **kwargs) 		# 🖼️ Надсилання напряму в чат
                logger.error("Немає chat_id для відправки одного фото.")                   			# 🚫 Критичний фолбек
                return None
            except RetryAfter as e:
                logger.warning("⏳ Rate limit (single) #%s, спимо…", attempt + 1)           			# 🧱 Впираємось у ліміт — чекаємо
                await self._retry_sleep(getattr(e, "retry_after", None), attempt)
            except (BadRequest, NetworkError) as e:
                logger.error("❌ BadRequest/NetworkError (single): %s", e)                  			# 🚨 Невиправна помилка — виходимо з циклу
                break

        await self._send_text_safe(update, context, msg.SEND_IMAGE_FAILED)                			# 💬 Акуратний фолбек
        return None

    # ==============================
    # 📦 ПАКЕТ (MEDIA GROUP)
    # ==============================
    async def _send_media_group_chunk(
        self,
        update: Update,
        context: CustomContext,
        media_items: List[MediaRef],
        *,
        first_caption: Optional[str],
        parse_mode: Optional[str],
        reply_to_message_id: Optional[int],
        disable_notification: Optional[bool],
        protect_content: Optional[bool],
        batch_index: int,
        total_batches: int,
    ) -> List[Message]:
        """
        📦 Надсилає один батч альбому (2..10 елементів).
        Якщо Telegram повертає помилку — автоматично розгортає батч в одиночні фото (fail‑open).
        """
        chat_id = update.effective_chat.id if update.effective_chat else None             			# 🆔 Куди надсилати
        has_message = bool(update.message)                                                			# 📩 Чи можемо відповісти на повідомлення

        media: List[InputMediaPhoto] = []                                                 			# 🧱 Формуємо payload для media group
        for idx, m in enumerate(media_items):
            kw: Dict[str, Any] = {}
            cap = first_caption if idx == 0 and first_caption else None                   			# 🏷️ Підпис лише на першому елементі
            kw.update(self._kv_if_set("caption", cap))
            kw.update(self._kv_if_set("parse_mode", parse_mode))
            media.append(InputMediaPhoto(media=m, **kw))                                  			# 🧩 Додаємо елемент до групи

        call_kwargs: Dict[str, Any] = {}                                                  			# 🧱 Додаткові параметри виклику
        call_kwargs.update(self._kv_if_set("reply_to_message_id", reply_to_message_id))
        call_kwargs.update(self._kv_if_set("disable_notification", disable_notification))
        call_kwargs.update(self._kv_if_set("protect_content", protect_content))

        for attempt in range(_MAX_RETRIES):
            try:
                if has_message and update.message:
                    sent = await update.message.reply_media_group(media=media, **call_kwargs)       	# 📦 Відправка як reply
                else:
                    if chat_id is None:
                        logger.error("Немає chat_id для відправки медіа-групи.")           			# 🚫 Нікуди надсилати — виходимо
                        return []
                    sent = await context.bot.send_media_group(chat_id=chat_id, media=media, **call_kwargs)  # 📦 Відправка напряму

                logger.debug("✅ Батч %s/%s відправлено: %s елементів", batch_index, total_batches, len(media))  # 🧾 Технічний лог
                return list(sent)
            except RetryAfter as e:
                logger.warning("⏳ Rate limit (group) #%s, спимо…", attempt + 1)             			# 🧱 Ліміт — чекаємо
                await self._retry_sleep(getattr(e, "retry_after", None), attempt)
            except (BadRequest, NetworkError) as e:
                logger.warning(
                    "❌ Помилка групи (батч %s/%s): %s. Fallback на одиночні.",
                    batch_index, total_batches, e,
                )                                                                           			# 🚨 Помилка — пробуємо розіслати по одному
                out: List[Message] = []
                for idx, single in enumerate(media_items):
                    single_caption = first_caption if idx == 0 and first_caption else None
                    s = await self._send_single_photo(
                        update, context, single,
                        caption=single_caption, parse_mode=parse_mode,
                        reply_to_message_id=reply_to_message_id,
                        disable_notification=disable_notification,
                        protect_content=protect_content,
                    )                                                                       			# 🖼️ Надсилаємо по одному
                    if s:
                        out.append(s)
                return out

        await self._send_text_safe(update, context, msg.SEND_IMAGE_FAILED)                			# 💬 Фінальний фолбек
        return []                                                                          			# 🏁 Нічого не відправили — пустий список
