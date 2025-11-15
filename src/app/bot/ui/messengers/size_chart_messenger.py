# 📬 app/bot/ui/messengers/size_chart_messenger.py
"""
📬 Відправляє згенеровані таблиці розмірів у Telegram.

🔹 Готує локальні PNG-файли до надсилання (перетворює у `InputFile`)
🔹 Делегує надсилання сервісу `ImageSender` (альбом/одиночні фото з ретраями)
🔹 Повідомляє користувача про помилки та логує результат
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import InputFile, Update                                      # 🤖 Telegram Bot API типи (можуть без stubs)

# 🔠 Системні імпорти
import asyncio                                                              # 🔄 Асинхронна обробка / CancelledError
import io                                                                   # 🧠 Буфер у пам'яті для файлів
import logging                                                              # 🧾 Логування дій месенджера
from pathlib import Path                                                    # 🛣️ Робота зі шляхами до файлів
from typing import Final, Iterable                                          # 🧰 Типи колекцій для прогріву

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.image_sender import ImageSender               # 🖼️ Сервіс надсилання фото
from app.bot.services.custom_context import CustomContext                   # 🧰 Розширений контекст бота
from app.bot.ui import static_messages as msg                               # 📝 Статичні повідомлення UI
from app.errors.exception_handler_service import ExceptionHandlerService    # 🛡️ Централізована обробка винятків
from app.shared.utils.logger import LOG_NAME                                # 🏷️ Кореневий логер проєкту

# ================================
# 🧾 ЛОГЕР МОДУЛЯ
# ================================
logger: Final = logging.getLogger(LOG_NAME)                                 # 🧾 Модульний логер


# ================================
# 🏛️ МЕСЕНДЖЕР ТАБЛИЦЬ РОЗМІРІВ
# ================================
class SizeChartMessenger:
    """
    📤 Готує та відправляє таблиці розмірів через `ImageSender`.
    """

    # ================================
    # ⚙️ ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(self, image_sender: ImageSender, exception_handler: ExceptionHandlerService) -> None:
        self.image_sender = image_sender                                      # 🖼️ DI: сервіс надсилання фото/альбомів
        self.exception_handler = exception_handler                            # 🛡️ DI: обробка винятків

    # ================================
    # 📣 ПУБЛІЧНИЙ API
    # ================================
    async def send(
        self,
        update: Update,
        context: CustomContext,
        image_paths: Iterable[str],
    ) -> None:
        """
        📦 Відправляє всі доступні таблиці розмірів як альбом або окремі фото.
        """
        try:
            if update.message is None:                                        # 🚫 Немає текстового повідомлення → нічого не шлемо
                return                                                       # 🛑 Коректно завершуємо

            image_list = list(image_paths)                                   # 📋 Приводимо Iterable до списку (для len())
            if not image_list:                                               # 🟡 Файлів немає — інформуємо користувача
                await update.message.reply_text(msg.SIZE_CHART_FAILED)
                return

            prepared_files = self._prepare_input_files(image_list)           # 🧰 Готуємо `InputFile`
            if not prepared_files:                                          # ⚠️ Не вдалося підготувати жодного файлу
                await update.message.reply_text(msg.SIZE_CHART_FAILED)
                return

            sent_media = await self.image_sender.send_images(                # 🚚 Делегуємо надсилання ImageSender
                update=update,
                context=context,
                images=prepared_files,
                caption="📏 Таблиця розмірів",
            ) or []

            logger.info(                                                     # 🧾 Лог успішної відправки
                "✅ Таблиці розмірів надіслано | chat_id=%s files_requested=%d files_sent=%d",
                getattr(update.effective_chat, "id", None),
                len(image_list),
                len(sent_media),
            )

        except asyncio.CancelledError:
            raise                                                           # 🔁 Проброс скасування задачі
        except Exception as error:  # noqa: BLE001
            await self.exception_handler.handle(error, update)              # 🛡️ Делегуємо обробку винятку

    # ================================
    # 🧱 ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _prepare_input_files(self, image_paths: Iterable[str]) -> list[InputFile]:
        """
        🔧 Перетворює шляхи до PNG у `InputFile`, читаючи байти у пам'ять.
        """
        prepared_files: list[InputFile] = []                                 # 📦 Колекція готових файлів

        for raw_path in image_paths:                                         # 🔁 Обходимо всі шляхи
            try:
                path = Path(raw_path)                                        # 🛣️ Створюємо Path
                if not path.is_file():                                       # ⚠️ Файл відсутній або некоректний
                    logger.warning("⚠️ Файл таблиці розмірів не існує: %s", raw_path)
                    continue                                                # ⏭️ Пропускаємо невалідний шлях

                buffer = io.BytesIO(path.read_bytes())                       # 🧠 Зчитуємо байти у пам'ять
                buffer.seek(0)                                               # 🔄 Переміщаємо курсор на початок
                prepared_files.append(InputFile(buffer, filename=path.name or "size_chart.png"))  # 📨 Формуємо InputFile

            except Exception as error:  # noqa: BLE001
                logger.warning("⚠️ Не вдалося підготувати файл таблиці: %s (%s)", raw_path, error)  # 🚨 Лог помилки

        return prepared_files                                                # 📤 Повертаємо список готових файлів
