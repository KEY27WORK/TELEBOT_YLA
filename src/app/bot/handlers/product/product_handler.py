# 📦 app/bot/handlers/product/product_handler.py
"""
📦 product_handler.py — обробник для запуску процесу обробки товару.

🔹 Клас `ProductHandler`:
- Отримує URL товару від користувача
- Делегує обробку сервісу `ProductProcessingService`
- Відправляє повідомлення через `ProductMessenger`
"""

# 🌐 Зовнішні бібліотеки
from telegram import Update									                                                    # 📩 Telegram-обʼєкт
from telegram.ext import CallbackContext						                                                # 🔁 Контекст виконання

# 🔠 Системні імпорти
import logging												                                                    # 📝 Логування
from typing import Optional									                                                    # 🧠 Типізація

# 🧩 Внутрішні модулі проєкту
from app.bot.ui.product_messenger import ProductMessenger				                                        # 📬 Відправка повідомлень
from app.errors.error_handler import error_handler					                                            # ❗️ Декоратор обробки помилок
from app.infrastructure.currency.currency_manager import CurrencyManager		                                # 💱 Менеджер валют
from app.infrastructure.product_processing.product_processing_service import ProductProcessingService	        # 🧠 Сервіс обробки товару
from app.shared.utils.logger import LOG_NAME						                                            # 📝 Назва логгера

logger = logging.getLogger(LOG_NAME)

# ================================
# 🏛️ КЛАС ОБРОБНИКА ТОВАРІВ
# ================================
class ProductHandler:
    """
    📦 Приймає запит на обробку товару та делегує роботу сервісам.
    """

    def __init__(
        self,
        currency_manager: CurrencyManager,						                                                # 💱 Менеджер валют
        processing_service: ProductProcessingService,				                                            # 🧠 Оркестратор обробки
        messenger: ProductMessenger,							                                                # 📬 Відправник повідомлень
    ):
        self.currency_manager = currency_manager					                                            # 💱 Курси валют
        self.processing_service = processing_service				                                            # 🧠 Логіка обробки
        self.messenger = messenger							                                                    # 📬 Надсилання блоків
        logger.info("🔧 ProductHandler успішно ініціалізовано.")

    @error_handler
    async def handle_url(
        self,
        update: Update,										                                                    # 📩 Обʼєкт Telegram Update
        context: CallbackContext,									                                            # 🔁 Контекст Telegram
        url: Optional[str] = None,									                                            # 🔗 Необовʼязковий URL товару
        update_currency: bool = True,									                                        # 💱 Оновити курси валют перед обробкою
    ):
        """
        📥 Отримує URL товару, запускає обробку та відправку результату.

        Args:
            update (Update): 📩 Обʼєкт Telegram Update
            context (CallbackContext): 🔁 Контекст Telegram
            url (Optional[str]): 🔗 Необовʼязковий URL товару
            update_currency (bool): 💱 Оновити курси валют перед обробкою
        """
        if not update.message:								                                            # 🚫 Немає повідомлення — нічого не робимо
            return

        final_url = url or update.message.text.strip()				                                    # 🔗 Витягуємо URL

        if update_currency:								                                                # 💱 Оновлюємо курси валют, якщо потрібно
            self.currency_manager.update_all_rates()

        logger.info(f"📩 Отримано запит на обробку товару: {final_url}")

        # 1. Викликаємо сервіс для збору всіх даних
        processed_data = await self.processing_service.process_url(final_url)

        if not processed_data:								                                            # ❌ Помилка при обробці — повідомляємо
            await update.message.reply_text("⚠️ Помилка при отриманні інформації про товар!")
            return

        # 2. Повідомляємо регіон
        await update.message.reply_text(
            f"🌍 Регіон сайту: <b>{processed_data.region_display}</b>",
            parse_mode="HTML"
        )

        # 3. Викликаємо сервіс для відправки всіх повідомлень
        await self.messenger.send(update, context, processed_data)
