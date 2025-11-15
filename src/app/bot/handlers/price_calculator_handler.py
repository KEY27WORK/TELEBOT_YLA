# 📬 app/bot/handlers/price_calculator_handler.py
"""
📬 Координує сценарій розрахунку повної вартості товару для Telegram-бота.

🔹 Приймає посилання та готує дані товару до обробки.
🔹 Делегує обчислення сервісу ціноутворення й формує звіт.
🔹 Інформує користувача про статус і обробляє виняткові ситуації.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import Update	# 🤖 Опис оновлень Telegram Bot API

# 🔠 Системні імпорти
import asyncio	# ⏱️ Асинхронні операції
import logging	# 🧾 Робота з логами
from decimal import Decimal	# 💰 Десяткова арифметика
from typing import Dict, Mapping, Optional, Tuple, List, cast	# 📐 Допоміжні типи

# 🧩 Внутрішні модулі проєкту
from app.bot.services.custom_context import CustomContext	# 🧠 Контекст обробки оновлення
from app.bot.ui.formatters.price_report_formatter import PriceReportFormatter	# 🧾 Формування тексту звіту
from app.bot.ui import static_messages as msg	# 💬 Статичні повідомлення для користувача
from app.config.config_service import ConfigService	# ⚙️ Зчитування конфігурацій
from app.config.setup.constants import AppConstants	# 🧷 Глобальні константи застосунку
from app.domain.currency.interfaces import IMoneyConverter	# 🔄 Контракт конвертера грошей
from app.domain.pricing.interfaces import (
    FullPriceDetails,	# 📊 Детальний результат розрахунку
    IPricingService,	# 🧮 Основний сервіс ціноутворення
    Money,	# 💵 Внутрішнє представлення грошової суми
    PricingContext,	# 🧾 Контекст розрахунку
)
from app.domain.products.entities import Currency, ProductInfo	# 📦 Дані товару з парсера
from app.errors.exception_handler_service import ExceptionHandlerService	# 🚨 Уніфікований обробник винятків
from app.infrastructure.currency.currency_manager import CurrencyManager	# 💱 Менеджер валютних курсів
from app.infrastructure.parsers.parser_factory import ParserFactory	# 🧩 Фабрика парсерів товарів
from app.shared.utils.logger import LOG_NAME	# 🏷️ Назва логера для підсистеми
from app.shared.utils.url_parser_service import UrlParserService	# 🔍 Нормалізація посилань

logger = logging.getLogger(LOG_NAME)	# 🧾 Створюємо іменований логер для модуля


# ================================
# 🏛️ ФІЧА / ГОЛОВНИЙ КЛАС
# ================================
class PriceCalculationHandler:
    """Оркеструє розрахунок повної ціни та відправлення повідомлення користувачу."""

    # ================================
    # 🧱 ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        *,
        currency_manager: CurrencyManager,
        parser_factory: ParserFactory,
        pricing_service: IPricingService,
        config_service: ConfigService,
        constants: AppConstants,
        exception_handler: ExceptionHandlerService,
        url_parser_service: UrlParserService,
        formatter: Optional[PriceReportFormatter] = None,
    ) -> None:
        """Налаштовує залежності обробника та готує форматер за замовчуванням."""
        self._currency_manager = currency_manager	# 💱 Працюємо з курсами валют
        self._parser_factory = parser_factory	# 🧩 Підбираємо відповідний парсер товару
        self._pricing_service = pricing_service	# 🧮 Використовуємо сервіс ціноутворення
        self._config = config_service	# ⚙️ Доступ до конфігураційних даних
        self._exception_handler = exception_handler	# 🚨 Делегуємо глобальну обробку помилок
        self._url_parser = url_parser_service	# 🔍 Нормалізуємо посилання перед парсингом
        self.const = constants	# 📦 Зберігаємо константи застосунку
        default_formatter = formatter or PriceReportFormatter()	# 🧾 Забезпечуємо форматування відповіді
        self._formatter = default_formatter	# 🧾 Зберігаємо обраний форматер

    # ================================
    # 🛰️ РЕЄСТРАЦІЯ ОБРОБНИКІВ / API
    # ================================
    async def handle_price_calculation(
        self,
        update: Update,
        context: CustomContext,
        url: str,
    ) -> None:
        """Запускає розрахунок ціни для переданого посилання.

        Args:
            update: Оновлення Telegram з вхідним повідомленням.
            context: Контекст обробки зі станом користувача.
            url: Посилання на товар, який потрібно прорахувати.
        """
        if not update.message:	# 🚫 Пропускаємо, якщо повідомлення відсутнє
            return	# ↩️ Немає що обробляти

        chat_id = update.effective_chat.id if update.effective_chat else "N/A"	# 💬 Зчитуємо ідентифікатор чату
        log_extra = {
            "chat_id": chat_id,	# 💬 Контекст: чат для трейсингу
            "url": url,	# 🔗 Контекст: посилання товару
        }	# 🧾 Додаємо контекст у лог

        try:
            logger.info("💸 PriceCalc: стартуємо обробку", extra=log_extra)	# 🪵 Фіксуємо початок сценарію
            try:
                await update.message.reply_text(
                    msg.PRICE_CALC_IN_PROGRESS,
                    parse_mode=getattr(self.const.UI, "DEFAULT_PARSE_MODE", None),
                )	# 📨 Повідомляємо користувача про старт розрахунку
            except Exception:	# noqa: BLE001 # ⚠️ Ігноруємо, якщо не вдалося повідомити
                pass	# ↩️ Жодних додаткових дій не потрібно

            _, message, _ = await self._calculate_and_format(url)	# 📊 Отримуємо готовий текст звіту
            await update.message.reply_text(
                message,
                parse_mode=self.const.UI.DEFAULT_PARSE_MODE,
            )	# 📤 Надсилаємо результат користувачу
            logger.info("💸 PriceCalc: повідомлення надіслано", extra=log_extra)	# 🪵 Фіксуємо успішне завершення
        except asyncio.CancelledError:	# 🛑 Обробляємо скасування
            logger.warning("💸 PriceCalc: сценарій скасовано", extra=log_extra)	# ⚠️ Відмічаємо скасований процес
            raise	# 🔁 Перекидаємо далі, щоб не приховати скасування
        except Exception as exc:	# noqa: BLE001 # 🚨 Ловимо несподівані помилки
            logger.exception("💸 PriceCalc: виникла помилка під час обробки", extra=log_extra)	# 🧨 Логуємо стектрейс
            await self._exception_handler.handle(exc, update)	# 🤝 Делегуємо централізованому обробнику

    # ================================
    # 🧠 КОМАНДИ / ОСНОВНІ МЕТОДИ
    # ================================
    async def _calculate_and_format(self, url: str) -> Tuple[ProductInfo, str, List[str]]:
        """
        Розраховує ціну, формує текст повідомлення та повертає службові дані.

        Returns:
            (ProductInfo, formatted_message, images)
        """
        await self._currency_manager.update_all_rates_if_needed()	# 💱 Актуалізуємо курси перед конвертацією
        converter: IMoneyConverter = self._currency_manager.get_money_converter()	# 🔄 Отримуємо конвертер грошей

        normalized_url = self._url_parser.normalize(url)	# 🔍 Нормалізуємо вхідне посилання
        parser = self._parser_factory.create_product_parser(normalized_url)	# 🧩 Обираємо відповідний парсер
        product_info = await parser.get_product_info()	# 📦 Завантажуємо дані товару

        if not self._is_valid_product_info(product_info):	# 🚫 Перевіряємо дані товару на валідність
            raise ValueError(f"ProductInfo є некоректним для url={url!r}: {product_info!r}")	# ❗ Пояснюємо причину збою

        price_money = Money(
            amount=product_info.price,	# 💵 Вихідна ціна товару
            currency=product_info.currency.value,	# 💱 Валюта ціни товару
        )	# 💰 Перемикаємося на Money для домену
        weight_kg = Decimal(product_info.weight_g) / Decimal("1000")	# ⚖️ Перетворюємо грами в кілограми
        weight_lbs = weight_kg * Decimal(str(self.const.LOGIC.CONVERSIONS.LBS_PER_KG))	# ⚖️ Розраховуємо фунти

        context = self._build_pricing_context(product_info)	# 🧾 Формуємо контекст витрат

        timeout_sec = self.const.LOGIC.TIMEOUTS.PRODUCT_PROCESS_SEC	# ⏳ Встановлюємо таймаут розрахунку
        pricing_task = asyncio.to_thread(
            self._pricing_service.calculate_full_price,
            price_money,
            weight_lbs,
            context,
            converter,
        )	# 🧵 Виносимо синхронний розрахунок у окремий потік
        details: FullPriceDetails = await asyncio.wait_for(
            pricing_task,
            timeout=timeout_sec,
        )	# ⏱️ Стежимо за виконанням із таймаутом

        message = self._formatter.format_message(product_info, details, context, converter)	# 🧾 Формуємо текст відповіді
        logger.debug("💸 PriceCalc: повідомлення сформовано успішно")	# 🪵 Фіксуємо факт форматування

        images: List[str] = [
            img
            for img in (product_info.images or tuple())
            if isinstance(img, str) and img
        ]	# 🖼️ Фільтруємо валідні URL зображень
        return product_info, message, images	# 📬 Повертаємо результат для повторного використання

    # ================================
    # 🛠️ CALLBACK-и / ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _build_pricing_context(self, pi: ProductInfo) -> PricingContext:
        """Повертає контекст ціноутворення, зібраний з конфігурації."""
        cfg_map = cast(
            Mapping[str, str],
            self._config.get("pricing.currency_map", {}) or {},
        )	# 🗺️ Мапа відповідності валют до регіонів
        region_key = cfg_map.get(pi.currency.value) or self.const.LOGIC.CURRENCY_MAP.get(
            pi.currency.value,
            "us",
        )	# 📍 Визначаємо регіон витрат

        context_data = cast(
            Dict[str, object],
            self._config.get(f"pricing.regional_costs.{region_key}", {}) or {},
        )	# 📚 Зчитуємо витрати для визначеного регіону
        if not context_data:	# 🚫 Перевіряємо наявність конфігурації
            logger.error(
                "pricing.regional_costs.%s не знайдено — використовуємо запасний профіль 'us'",
                region_key,
            )	# 🛟 Логуємо перехід на запасну конфігурацію
            context_data = cast(
                Dict[str, object],
                self._config.get("pricing.regional_costs.us", {}) or {},
            )	# 🔁 Підвантажуємо дефолтні регіональні витрати

        currency_code = pi.currency.value	# 💱 Фіксуємо валюту контексту

        def to_decimal(value: object) -> Decimal:
            """Перетворює довільне значення на Decimal або повертає 0."""
            try:
                return Decimal(str(value))	# 🔄 Намагаємось уніфікувати значення
            except Exception:	# noqa: BLE001 # ⚠️ Некоректний формат
                return Decimal("0")	# 0️⃣ Повертаємо нульове значення

        return PricingContext(
            local_delivery_cost=Money(
                to_decimal(context_data.get("local_delivery_cost", 0)),
                currency_code,
            ),	# 🚚 Вартість локальної доставки
            ai_commission=Money(
                to_decimal(context_data.get("ai_commission", 0)),
                currency_code,
            ),	# 🤖 Комісія ШІ-сервісу
            phone_number_cost=Money(
                to_decimal(context_data.get("phone_number_cost", 0)),
                currency_code,
            ),	# 📞 Витрати на віртуальний номер
            country_code=str(context_data.get("country_code", "us")),	# 🌍 Код країни для митних правил
        )	# 🧾 Повертаємо повноцінний контекст ціноутворення

    # ================================
    # 🧪 CALLBACK-и / ДОПОМІЖНІ МЕТОДИ
    # ================================
    @staticmethod
    def _is_valid_product_info(pi: object) -> bool:
        """Перевіряє, що об'єкт містить валідні дані товару."""
        if not isinstance(pi, ProductInfo):	# 🧱 Маємо отримати саме ProductInfo
            return False	# 🚫 Невідомий тип даних
        try:
            price_ok = (pi.price is not None) and (float(pi.price) >= 0.0)	# 💵 Ціна повинна бути невід'ємною
        except (TypeError, ValueError):	# ⚠️ Значення не конвертується у число
            price_ok = False	# 🚫 Ціна некоректна
        try:
            weight_ok = (pi.weight_g is not None) and (int(pi.weight_g) >= 0)	# ⚖️ Вага також не повинна бути від'ємною
        except (TypeError, ValueError):	# ⚠️ Не вдалося перетворити вагу
            weight_ok = False	# 🚫 Вага некоректна
        currency_ok = isinstance(pi.currency, Currency)	# 💱 Валюта повинна бути відомою переліку
        title_ok = isinstance(pi.title, str) and pi.title.strip() != ""	# 🏷️ Назва товару не має бути порожньою
        return price_ok and weight_ok and currency_ok and title_ok	# ✅ Всі критерії перевірені


__all__ = ["PriceCalculationHandler"]	# 📦 Експортуємо доступний інтерфейс модуля
