# 🧾 app/bot/ui/formatters/price_report_formatter.py
"""
🧾 Форматує результати розрахунку ціни у повідомлення Telegram (HTML).

🔹 Підтримує як мінімальний `PriceBreakdown`, так і розширений `FullPriceDetails`
🔹 Відображає суми у декількох валютах (залежно від регіону користувача)
🔹 Додає довідкові рядки (валюта звіту, походження тарифів, референс у USD для гривневих тоталів)
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (відсутні)

# 🔠 Системні імпорти
from decimal import Decimal, ROUND_HALF_UP                           # 🔢 Операції з десятковими сумами
from html import escape as html_escape                               # 🧼 Безпечні посилання в HTML
from typing import Dict, Final, Iterable, Protocol, Union, runtime_checkable, cast  # 🧰 Типізація та протоколи

# 🧩 Внутрішні модулі проєкту
from app.domain.currency.interfaces import (                         # 💱 Інтерфейси роботи з валютами
    ICurrencyConverter,
    IMoneyConverter,
    Money as CurrencyMoney,
    CurrencyCode,
)
from app.domain.pricing.interfaces import (                          # 💸 Доменні DTO прайсингу
    FullPriceDetails,
    PriceBreakdown,
    PriceInput,
    PricingContext,
)
from app.domain.products.entities import ProductInfo                 # 🛍 DTO товару (назва, фото тощо)


# ================================
# 🧾 ПРОТОКОЛ ГРОШОВОГО DTO
# ================================
@runtime_checkable
class MoneyLike(Protocol):
    """
    📐 Мінімальний контракт для об'єктів, що поводяться як Money (amount + currency).
    """

    @property
    def amount(self) -> Decimal:
        """Поточне значення суми."""
        ...

    @property
    def currency(self) -> Union[str, CurrencyCode]:
        """Поточний код валюти (ISO-4217)."""
        ...


# ================================
# 💬 КЛАС ФОРМАТЕРА ПОВІДОМЛЕНЬ
# ================================
class PriceReportFormatter:
    """
    💬 Формує готові HTML-повідомлення зі звітами прайсингу.
    """

    _BULLET: Final[str] = "•"                                         # 🔹 Маркер для списків
    _CURRENCY_SYMBOLS: Final[Dict[str, str]] = {                      # 💱 Символи популярних валют
        "USD": "$",
        "EUR": "€",
        "UAH": "₴",
        "GBP": "£",
        "PLN": "zł",
    }
    _UA_FLAG: Final[str] = "🇺🇦"                                      # 🇺🇦 Прапор країни доставки за замовчуванням
    _UA_NAME: Final[str] = "Україна"                                  # 🏷️ Назва країни доставки за замовчуванням

    # ================================
    # 🧮 ДОПОМІЖНІ ФОРМАТЕРИ
    # ================================
    @staticmethod
    def _fmt_money(money: MoneyLike) -> str:
        """
        Форматує суму у вигляді `123.45 USD`.
        """
        amount = Decimal(money.amount)                                # 🔢 Копія суми як Decimal
        currency = str(money.currency)                                # 🏷️ Рядок з кодом валюти
        return f"{amount:.2f} {currency}"                             # 📤 Повертаємо уніфікований формат

    @staticmethod
    def _ref_usd_line(
        total: MoneyLike,
        converter: Union[ICurrencyConverter, IMoneyConverter],
    ) -> str | None:
        """
        Повертає рядок з довідковою сумою у USD (для гривневих тоталів).
        """
        currency_code = str(total.currency).upper()                   # 🏷️ Код валюти тоталу
        if currency_code != "UAH":                                    # 🛑 Конвертація лише для гривневих сум
            return None

        try:
            amount_uah = Decimal(total.amount)                        # 🔢 Вихідна сума в UAH
            if hasattr(converter, "convert_money"):                   # 🔄 Новий decimal-конвертер
                money_uah = CurrencyMoney(                            # 💸 Обгортаємо суму як Money
                    amount=amount_uah,
                    currency=cast(CurrencyCode, "UAH"),
                )
                converted = cast(IMoneyConverter, converter).convert_money(
                    money_uah,
                    cast(CurrencyCode, "USD"),
                )
                usd_amount = Decimal(converted.amount)                # 💵 Зчитуємо суму у USD
            else:                                                     # 🔁 Легасі float-конвертер
                legacy_amount = cast(
                    ICurrencyConverter,
                    converter,
                ).convert(float(amount_uah), "UAH", "USD")
                usd_amount = Decimal(str(legacy_amount))              # 🧮 Нормалізуємо тип
            return f"≈ {usd_amount:.2f} USD (довідково)"              # 📤 Друкуємо референс
        except Exception:
            return None                                               # ⚠️ У разі помилки рядок ігноруємо

    # ================================
    # 🏗️ ПУБЛІЧНЕ API
    # ================================
    def format_message(
        self,
        product: ProductInfo,
        details: Union[PriceBreakdown, FullPriceDetails],
        price_input: Union[PriceInput, PricingContext],
        converter: Union[ICurrencyConverter, IMoneyConverter],
    ) -> str:
        """
        Будує HTML-повідомлення зі звітом про ціну.
        """
        if isinstance(details, PriceBreakdown):                       # 🔀 Мінімальний звіт?
            return self._format_breakdown(product, details, price_input, converter)
        return self._format_full_details(product, details, price_input, converter)

    @staticmethod
    def _primary_image_url(product: ProductInfo) -> str | None:
        """
        Повертає перше валідне зображення (image_url → gallery).
        """
        if product.image_url:
            return product.image_url
        for image in product.images or ():
            if isinstance(image, str) and image.strip():
                return image
        return None

    def _image_block(self, product: ProductInfo) -> list[str]:
        """
        Формує блок із посиланням на головне зображення, якщо воно існує.
        """
        url = self._primary_image_url(product)
        if not url:
            return []
        safe_url = html_escape(url, quote=True)
        return [
            f"🖼️ Зображення: <a href=\"{safe_url}\">Посилання</a>",
            safe_url,
            "",
        ]

    # ================================
    # 🧾 МІНІМАЛЬНИЙ ЗВІТ (PriceBreakdown)
    # ================================
    def _format_breakdown(
        self,
        product: ProductInfo,
        details: PriceBreakdown,
        price_input: Union[PriceInput, PricingContext],
        converter: Union[ICurrencyConverter, IMoneyConverter],
    ) -> str:
        """
        Форматує короткий квот (без детальної розбивки).
        """
        target_currency = (                                           # 🎯 Визначаємо валюту звіту
            price_input.target_currency
            if isinstance(price_input, PriceInput)
            else str(details.total.currency)
        )

        lines = [                                                     # 📋 Колекція рядків повідомлення
            *self._image_block(product),
            f"🛍 <b>{product.title}</b>",
            "",
            f"💱 Валюта звіту: <b>{target_currency}</b>",
            "",
            "💸 <b>Прайс-квота</b>",
            f"{self._BULLET} База: {self._fmt_money(details.base_converted)}",
            f"{self._BULLET} Доставка: {self._fmt_money(details.shipping)}",
            f"{self._BULLET} Комісія: {self._fmt_money(details.commission)}",
            f"{self._BULLET} Знижка: −{self._fmt_money(details.discount)}",
            f"{self._BULLET} Сума до округлення: {self._fmt_money(details.total_before_round)}",
            "",
            f"✅ <b>Разом до оплати: {self._fmt_money(details.total)}</b>",
        ]

        usd_ref = self._ref_usd_line(details.total, converter)        # 🔎 Пробуємо побудувати USD-рівень
        if usd_ref:                                                   # ✅ Якщо вдалось — додаємо
            lines.append(usd_ref)

        return "\n".join(lines)                                       # 📤 Повертаємо HTML-блок

    # ================================
    # 📊 ПОВНИЙ ЗВІТ (FullPriceDetails)
    # ================================
    def _format_full_details(
        self,
        product: ProductInfo,
        details: FullPriceDetails,
        price_input: Union[PriceInput, PricingContext],
        converter: Union[ICurrencyConverter, IMoneyConverter],
    ) -> str:
        """
        Форматує розширений звіт з розбивкою за доставками, знижками та прибутком.
        """
        target_currency = str(details.sale_price.currency)            # 🎯 Валюта звіту
        region_code = (                                               # 🌍 Код регіону для пріоритету валют
            price_input.country_code if isinstance(price_input, PricingContext) else None
        )

        sale_multi = self._format_multi_currency(details.sale_price, converter, region_code)              # 💵 Продажна ціна
        sale_rounded_multi = self._format_multi_currency(details.sale_price_rounded, converter, region_code)  # 💢 Округлена ціна
        discounted_multi = self._format_multi_currency(details.discounted_price, converter, region_code)  # 🎯 Ціна після знижки
        local_delivery_multi = self._format_multi_currency(details.local_delivery, converter, region_code)    # 📦 Локальна доставка
        intl_delivery_multi = self._format_multi_currency(details.international_delivery, converter, region_code)  # ✈️ Міжнародна доставка
        full_delivery_multi = self._format_multi_currency(details.full_delivery, converter, region_code)    # 🚚 Повна доставка
        protection_multi = self._format_multi_currency(details.protection, converter, region_code)         # 🛡️ Страхування
        cost_base_multi = self._format_multi_currency(details.cost_without_delivery, converter, region_code)  # 🧾 Собівартість без доставки
        cost_total_multi = self._format_multi_currency(details.cost_price, converter, region_code)          # 🧾 Собівартість з доставкою
        profit_multi = self._format_multi_currency(details.profit, converter, region_code)                 # 📊 Прибуток
        profit_rounded_multi = self._format_multi_currency(details.profit_rounded, converter, region_code) # 📊 Прибуток після округлення

        round_delta_amount = details.sale_price_rounded.amount - details.sale_price.amount                 # 🔁 Дельта між цінами
        round_delta_money = CurrencyMoney(                                                                 # 💵 Money для дельти
            amount=Decimal(round_delta_amount),
            currency=cast(CurrencyCode, target_currency),
        )
        round_delta_multi = self._format_multi_currency(round_delta_money, converter, region_code)         # 🔁 Дельта у різних валютах

        origin_flag, origin_label = self._region_display(region_code)                                      # 🚩 Прапор та назва регіону

        lines = [                                                     # 📋 Основний блок повідомлення
            *self._image_block(product),
            f"🛍 <b>{product.title}</b>",
            "",
            f"💱 Валюта звіту: <b>{target_currency}</b>",
            "",
            f"💵 Ціна продажу: {sale_multi}",
            f"💢 Округлена ціна: {sale_rounded_multi}",
            f"🎯 Ціна після знижки: {discounted_multi}",
            f"🔁 Дельта округлення: {round_delta_multi} (UAH: {details.round_delta_uah:.2f})",
            "",
            f"⚖️ Вага: {details.weight_lbs:.2f} фунтів",
            f"📦 Локальна доставка {origin_flag} {origin_label}: {local_delivery_multi}",
            f"📦 Meest доставка: {intl_delivery_multi}",
            f"🚚 Повна доставка до {self._UA_FLAG} {self._UA_NAME} з {origin_flag} {origin_label}: {full_delivery_multi}",
            f"🛡️ Страховка Navidium: {protection_multi}",
            "",
            f"🏷️ Собівартість без доставки: {cost_base_multi}",
            f"🏷️ Собівартість з доставкою: {cost_total_multi}",
            "",
            f"📉 Корекція націнки: {details.markup_adjustment:+.2f} п.п.",
            f"📈 Націнка: {details.markup:.2f}%",
            "",
            f"📊 Чистий прибуток: {profit_multi}",
            f"📊 Прибуток (після округлення): {profit_rounded_multi}",
        ]

        if isinstance(price_input, PricingContext):                   # 🌍 Додаємо інформацію про регіон тарифів
            lines.append("")
            lines.append(f"🌍 Країна тарифів: {origin_flag} <b>{price_input.country_code}</b> ({origin_label})")

        usd_ref = self._ref_usd_line(details.sale_price_rounded, converter)  # 🔎 Референс у USD (для гривневих звітів)
        if usd_ref:
            lines.append(usd_ref)

        return "\n".join(lines)                                       # 📤 Повертаємо повний HTML

    # ================================
    # 💱 БАГАТОВАЛЮТНІ СУМИ
    # ================================
    def _format_multi_currency(
        self,
        money: MoneyLike,
        converter: Union[ICurrencyConverter, IMoneyConverter],
        region_code: str | None,
    ) -> str:
        """
        Повертає суму у декількох валютах (порядок залежить від регіону).
        """
        base_currency = str(money.currency).upper()                   # 🏷️ Початкова валюта
        ordered_codes = self._build_currency_order(region_code, base_currency)  # 📋 Список пріоритетних кодів
        rendered: list[str] = []                                      # 🧾 Колекція відформатованих сум
        used: set[str] = set()                                        # 🪪 Уникаємо повторів валют

        for code in ordered_codes:                                    # 🔁 Проходимось по валютам
            upper = code.upper()
            if upper in used:                                         # 🚫 Уникаємо duplicates
                continue
            converted = self._convert_money_amount(money, converter, upper)  # 🔄 Конвертуємо значення
            if converted is None:                                     # ⚠️ Якщо не вдалося — пропускаємо
                continue
            formatted_amount = self._format_decimal(converted)        # 🧮 Форматуємо Decimal до 2 знаків
            symbol = self._currency_symbol(upper)                     # 💱 Беремо символ валюти (якщо є)
            rendered.append(f"{symbol}{formatted_amount}" if symbol else f"{formatted_amount} {upper}")  # 🧾 Додаємо рядок
            used.add(upper)                                           # 🗂️ Позначаємо валюту як використану

        if not rendered:                                              # 🟡 Якщо жодну валюту не змогли відрендерити
            return self._fmt_money(money)
        return " / ".join(rendered)                                   # 📤 Повертаємо комбінацію валют

    @staticmethod
    def _build_currency_order(region_code: str | None, base_currency: str) -> list[str]:
        """
        Визначає порядок валют залежно від регіону користувача.
        """
        region = (region_code or "").lower()                          # 🌍 Нормалізуємо код регіону
        preferred_map: Dict[str, list[str]] = {                       # 🗺️ Пріоритети валют за регіонами
            "uk": ["GBP", "EUR", "USD", "UAH"],
            "gb": ["GBP", "EUR", "USD", "UAH"],
            "eu": ["EUR", "USD", "UAH"],
            "us": ["USD", "EUR", "UAH"],
        }
        preferred = preferred_map.get(region, [])                     # ✅ Першочергові валюти (якщо є)
        fallback = [base_currency.upper(), "USD", "EUR", "UAH", "GBP"]  # 📦 Резервний список

        ordered: list[str] = []                                       # 📋 Сукупний список без дублікатів
        for code in preferred + fallback:                             # 🔁 Об'єднуємо пріоритети та дефолти
            upper = code.upper()
            if upper not in ordered:
                ordered.append(upper)
        return ordered                                                # 📤 Повертаємо остаточний порядок

    @classmethod
    def _currency_symbol(cls, code: str) -> str:
        """
        Повертає символ валюти (якщо підтримується).
        """
        return cls._CURRENCY_SYMBOLS.get(code.upper(), "")

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        """
        Форматує Decimal до рядка з двома знаками після коми.
        """
        rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # 🎯 Округлення HALF_UP
        return f"{rounded:.2f}"                                     # 📤 Перетворюємо на рядок

    def _convert_money_amount(
        self,
        money: MoneyLike,
        converter: Union[ICurrencyConverter, IMoneyConverter],
        destination_currency: str,
    ) -> Decimal | None:
        """
        Конвертує суму у зазначену валюту (Decimal або None, якщо не вдалося).
        """
        source_currency = str(money.currency).upper()                # 🏷️ Початковий код валюти
        target_currency = destination_currency.upper()               # 🎯 Цільовий код валюти

        if target_currency == source_currency:                       # ♻️ Немає потреби конвертувати
            return self._to_decimal(money.amount)

        try:
            amount = self._to_decimal(money.amount)                  # 🔢 Базова сума як Decimal
            if hasattr(converter, "convert_money"):                  # 🔄 Новий IMoneyConverter
                src_money = CurrencyMoney(amount=amount, currency=cast(CurrencyCode, source_currency))
                converted = cast(IMoneyConverter, converter).convert_money(
                    src_money,
                    cast(CurrencyCode, target_currency),
                )
                return self._to_decimal(converted.amount)
            if hasattr(converter, "convert"):                        # 🔁 Легасі ICurrencyConverter
                legacy_value = cast(ICurrencyConverter, converter).convert(
                    float(amount),
                    source_currency,
                    target_currency,
                )
                return self._to_decimal(legacy_value)
        except Exception:
            return None                                              # ⚠️ У разі помилки повертаємо None
        return None                                                  # 🟡 Конвертація не підтримується

    @staticmethod
    def _to_decimal(value: Union[Decimal, float, int, str]) -> Decimal:
        """
        Акуратно перетворює довільне числове значення у Decimal.
        """
        if isinstance(value, Decimal):                               # ✅ Якщо вже Decimal — повертаємо як є
            return value
        return Decimal(str(value))                                   # 🔄 Інакше приводимо через str()

    @classmethod
    def _region_display(cls, region_code: str | None) -> tuple[str, str]:
        """
        Повертає (emoji-прапор, людську назву) для регіону тарифів.
        """
        mapping: Dict[str, tuple[str, str]] = {                      # 🗺️ Відомі відповідності регіонів
            "us": ("🇺🇸", "США"),
            "uk": ("🇬🇧", "Британія"),
            "gb": ("🇬🇧", "Британія"),
            "eu": ("🇪🇺", "ЄС"),
            "ua": (cls._UA_FLAG, cls._UA_NAME),
        }
        region = (region_code or "").lower()                         # 🌍 Нормалізований код
        if region in mapping:                                        # ✅ Якщо відомий — повертаємо готовий запис
            return mapping[region]
        if len(region) == 2 and region.isalpha():                    # 🌐 Будуємо прапор з ISO-коду
            flag = "".join(chr(0x1F1E6 + ord(ch.upper()) - ord("A")) for ch in region)
            return flag, region.upper()
        return "🌍", (region_code or "N/A").upper()                   # 🌍 Дефолт для невідомих регіонів
