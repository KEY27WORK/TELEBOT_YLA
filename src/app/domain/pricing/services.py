# 📦 app/domain/pricing/services.py
"""
📦 Чистий сервіс розрахунку вартості товару для доменного шару.

🔹 Інкапсулює повний конвеєр обчислення ціни без побічних ефектів.
🔹 Працює виключно через доменні інтерфейси конвертера та доставки.
🔹 Утримує конфігураційні параметри формули у відокремленому контейнері.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                # 🪵 Логування кроків розрахунку
import math                                                   # 🧮 Крокове страхування Navidium
from dataclasses import dataclass                             # 🧱 Immutable-конфіг сервісу
from decimal import Decimal                                   # 💵 Точні гроші (без float)
from typing import Tuple                                      # 🧰 Пара (markup, adjustment)

# 🧩 Внутрішні модулі проєкту
from .interfaces import (
    IPricingService,
    PricingContext,
    FullPriceDetails,
    Money as PMoney,                                          # 💵 Money з домену прайсингу
)
from .rounding import q2                                      # 🔁 Нормалізоване округлення до 2 знаків
from app.domain.currency.interfaces import (                  # 💱 Новий Decimal-конвертер
    IMoneyConverter,
    Money as CMoney,                                          # 💵 Money з домену currency
    CurrencyCode,
)
from app.domain.delivery.interfaces import (                  # 🚚 Абстракція сервісу доставки
    IDeliveryService,
    DeliveryQuote,
)
from app.shared.utils.logger import LOG_NAME                  # 🏷️ Базове імʼя логера

logger = logging.getLogger(f"{LOG_NAME}.domain.pricing")      # 🧾 Іменований логер сервісу


# ================================
# ⚙️ ДОДАТКОВІ НАЛАШТУВАННЯ
# ================================
@dataclass(frozen=True, slots=True)
class PricingConfig:
    """Конфігураційні параметри формули прайсингу."""
    discount_percent: Decimal = Decimal("15")  # 🎯 Відсоток знижки магазину

    # 🛡️ Страховка Meest
    # Режими:
    #   - "none"         — не використовувати страховку
    #   - "fixed"        — фіксована сума в USD, додається до full_delivery
    #   - "percent_cost" — % від собівартості (до націнки), додається перед маркапом
    #   - "percent_final"— %, який нараховується від фінальної ціни після округлення
    meest_insurance_mode: str = "none"
    meest_insurance_fixed_usd: Decimal = Decimal("0.00")
    meest_insurance_percent: Decimal = Decimal("0.00")


# ================================
# 🏛️ ГОЛОВНИЙ ДОМЕННИЙ СЕРВІС
# ================================
class PricingService(IPricingService):
    """💸 Доменний сервіс, що виконує **чистий** конвеєр розрахунку ціни."""

    def __init__(self, delivery_service: IDeliveryService, cfg: PricingConfig | None = None) -> None:
        """
        ⚙️ Прив'язує сервіс до абстрактного доставника та базового конфіга.

        Args:
            delivery_service: Інтерфейс для отримання тарифів доставки.
            cfg: Кастомний набір параметрів розрахунку, опційний.
        """
        self._delivery = delivery_service                               # 🚚 Зберігаємо сервіс доставки
        cfg_fallback = cfg or PricingConfig()                            # ⚙️ Визначаємо активний конфіг
        self._cfg = cfg_fallback                                        # 🧾 Кешуємо конфігурацію у сервісі

    # ================================
    # 🔢 ПУБЛІЧНИЙ API РОЗРАХУНКУ
    # ================================
    def calculate_full_price(
        self,
        price: PMoney,                                  # 💵 Базова ціна товару у ВАЛЮТІ ТОВАРУ
        weight_lbs: Decimal,                            # ⚖️ Вага у фунтах (Decimal)
        context: PricingContext,                        # 🧭 Money-поля: local_delivery_cost, ai_commission, phone_number_cost
        converter: IMoneyConverter,                     # 💱 Точний Decimal-конвертер
    ) -> FullPriceDetails:
        """
        🚀 Запускає покроковий розрахунок повної вартості товару в USD.

        Args:
            price: Початкова ціна товару в оригінальній валюті.
            weight_lbs: Вага товару у фунтах, підготовлена на стороні парсера.
            context: Додаткові витрати для регіону продавця.
            converter: Сервіс конвертації грошей у форматі Decimal.

        Returns:
            FullPriceDetails: Повний набір агрегованих сум у USD.
        """
        product_price = q2(price.amount)                                # 💵 Нормалізуємо суму товару
        weight_lbs_clean = q2(weight_lbs)                               # ⚖️ Округлюємо вагу фунтів
        local_delivery_amount = q2(context.local_delivery_cost.amount)  # 🚚 Локальна доставка (Decimal)
        ai_commission_amount = q2(context.ai_commission.amount)         # 🤖 Комісія сервісу
        phone_cost_amount = q2(context.phone_number_cost.amount)        # 📞 Вартість номера

        logger.info(
            f"💸 Pricing started | base_price={product_price} {price.currency} "
            f"weight={weight_lbs_clean} lbs country={context.country_code} "
            f"local_delivery={local_delivery_amount} {context.local_delivery_cost.currency} "
            f"ai_commission={ai_commission_amount} {context.ai_commission.currency} "
            f"phone_cost={phone_cost_amount} {context.phone_number_cost.currency}"
        )

        # --- 🔄 Підготовка: уніфікуємо все у USD ---
        original_price_usd = self._to_usd(price, converter)                        # 💵 Ціна товару в USD
        local_delivery_usd = self._to_usd(context.local_delivery_cost, converter)  # 🚚 Локальна доставка в USD
        ai_commission_usd = self._to_usd(context.ai_commission, converter)         # 🤖 Комісія в USD
        phone_cost_usd = self._to_usd(context.phone_number_cost, converter)        # 📞 Вартість номера в USD
        meest_insurance_mode = self._cfg.meest_insurance_mode                      # ⚙️ Активний режим страховки
        meest_insurance_amount_usd = Decimal("0")                                 # 🛡️ Фактична сума страховки Meest
        meest_insurance_percent = Decimal("0")                                    # 📊 Відсоток (для percent_final)
        logger.info(
            "🔄 USD normalization | "
            f"product={product_price} {price.currency} → {original_price_usd.amount} USD, "
            f"local_delivery={local_delivery_amount} {context.local_delivery_cost.currency} → {local_delivery_usd.amount} USD, "
            f"ai_commission={ai_commission_amount} {context.ai_commission.currency} → {ai_commission_usd.amount} USD, "
            f"phone_cost={phone_cost_amount} {context.phone_number_cost.currency} → {phone_cost_usd.amount} USD"
        )

        # --- 🛡️ Крок 0: Вартість страховки (Navidium) — від ЦІНИ ДО знижки ---
        protection_usd_amt = q2(self._navidium_cost(original_price_usd.amount))    # 🛡️ Страховка Navidium
        logger.info(
            f"🛡️ Navidium insurance | base_price={original_price_usd.amount} USD → protection={protection_usd_amt} USD"
        )

        # --- 📉 Крок 1: Знижка — ТІЛЬКИ на ціну товару ---
        discounted_price_usd = q2(self._apply_discount(original_price_usd.amount)) # 📉 Ціна зі знижкою
        logger.info(
            f"📉 Discount applied | percent={self._cfg.discount_percent}% "
            f"base_price={original_price_usd.amount} USD → discounted_price={discounted_price_usd} USD"
        )

        # --- ✈️ Крок 2: Міжнародна доставка (вага → грам) ---
        weight_g = self._lbs_to_grams(weight_lbs)                                  # ⚖️ Переводимо фунти у грами
        quote: DeliveryQuote = self._delivery.quote(                    # ✈️ Запитуємо котирування від сервісу доставки
            country=context.country_code,
            method="air",
            type_="courier",
            weight_g=weight_g,
            volumetric_weight_g=None,
        )                                                                           # ✈️ Отримуємо тариф по доставці
        quote_price_normalized = q2(quote.price)                                   # 💵 Нормалізуємо вартість доставки
        meest_delivery_money = self._to_usd(PMoney(quote_price_normalized, quote.currency), converter)  # ✈️ Міжнародна доставка в USD
        meest_delivery_usd_amt = meest_delivery_money.amount                       # 💵 Decimal сума доставки
        logger.info(
            f"✈️ Delivery quote | weight={weight_lbs_clean} lbs → {weight_g} g, "
            f"quote={quote_price_normalized} {quote.currency} → {meest_delivery_usd_amt} USD"
        )

        # --- 📦 Крок 3: Повна доставка ---
        full_delivery_usd_amt = q2(local_delivery_usd.amount + meest_delivery_usd_amt)  # 📦 Сукупна доставка
        logger.info(
            f"📦 Delivery total | local={local_delivery_usd.amount} USD + intl={meest_delivery_usd_amt} USD "
            f"→ full_delivery={full_delivery_usd_amt} USD"
        )

        # 🛡️ Meest insurance (fixed) → частина доставки, впливає на маркап
        if self._cfg.meest_insurance_mode == "fixed" and self._cfg.meest_insurance_fixed_usd > 0:
            fixed_insurance = q2(self._cfg.meest_insurance_fixed_usd)
            full_delivery_usd_amt = q2(full_delivery_usd_amt + fixed_insurance)
            meest_insurance_amount_usd = fixed_insurance
            logger.info(
                "🛡️ Meest insurance (fixed) | +%s USD → full_delivery=%s USD",
                fixed_insurance,
                full_delivery_usd_amt,
            )

        # --- 🧾 Крок 4: Собівартість («ціна для друзів») ---
        cost_price_usd_amt = q2(
            discounted_price_usd
            + protection_usd_amt
            + ai_commission_usd.amount
            + phone_cost_usd.amount
            + full_delivery_usd_amt
        )                                                                          # 🧾 Собівартість з доставкою
        cost_without_delivery_usd_amt = q2(
            discounted_price_usd
            + protection_usd_amt
            + ai_commission_usd.amount
            + phone_cost_usd.amount
        )                                                                          # 🧾 Собівартість без доставки
        logger.info(
            "🧾 Cost build-up | "
            f"discounted_price={discounted_price_usd} USD + protection={protection_usd_amt} USD "
            f"+ ai_commission={ai_commission_usd.amount} USD + phone_cost={phone_cost_usd.amount} USD "
            f"+ full_delivery={full_delivery_usd_amt} USD → cost_price={cost_price_usd_amt} USD"
        )

        # 🛡️ Meest insurance (percent від собівартості)
        if (
            self._cfg.meest_insurance_mode == "percent_cost"
            and self._cfg.meest_insurance_percent > 0
        ):
            insurance_usd_amt = q2(
                cost_price_usd_amt * self._cfg.meest_insurance_percent / Decimal("100")
            )
            cost_price_usd_amt = q2(cost_price_usd_amt + insurance_usd_amt)
            meest_insurance_amount_usd = insurance_usd_amt
            meest_insurance_percent = self._cfg.meest_insurance_percent
            logger.info(
                "🛡️ Meest insurance (percent_cost) | rate=%s%% → +%s USD → cost_price=%s USD",
                self._cfg.meest_insurance_percent,
                insurance_usd_amt,
                cost_price_usd_amt,
            )

        # --- 📈 Крок 5: Фінальна маржинальна націнка ---
        final_markup, markup_adjustment = self._final_markup(
            price_usd=discounted_price_usd,
            delivery_usd=full_delivery_usd_amt,
        )                                                                           # 📈 Отримуємо пару (markup, adjustment)
        logger.info(
            f"📈 Markup decision | discounted_price={discounted_price_usd} USD "
            f"delivery_total={full_delivery_usd_amt} USD → final_markup={final_markup}% adjustment={markup_adjustment}%"
        )

        # --- 💵 Крок 6: Ціна продажу та прибуток (до округлення) ---
        sale_price_usd_amt = q2(
            cost_price_usd_amt * (Decimal("1") + final_markup / Decimal("100"))
        )                                                                          # 💵 Розраховуємо ціну продажу
        profit_usd_amt = q2(sale_price_usd_amt - cost_price_usd_amt)              # 💰 Прибуток до округлення
        logger.info(
            f"💵 Sale (pre-round) | cost_price={cost_price_usd_amt} USD markup={final_markup}% "
            f"→ sale_price={sale_price_usd_amt} USD profit={profit_usd_amt} USD"
        )

        # --- 🔁 Крок 7: Маркетингове округлення «через UAH» до найближчих 10 ↑ ---
        usd_to_uah = self._rate(converter, Decimal("1"), "USD", "UAH")            # 🔄 Курс USD→UAH (Decimal)
        sale_price_uah = sale_price_usd_amt * usd_to_uah                          # 💴 Ціна продажу в гривні
        sale_price_rounded_uah = self._ceil_to_10_uah(sale_price_uah)            # 🔔 Округлена ціна в гривні
        sale_price_rounded_usd_amt = q2(sale_price_rounded_uah / usd_to_uah)     # 💵 Повертаємо округлення в USD
        profit_rounded_usd_amt = q2(sale_price_rounded_usd_amt - cost_price_usd_amt)  # 💰 Прибуток після округлення
        delta_uah = q2(sale_price_rounded_uah - sale_price_uah)                  # 🔄 Дельта округлення в гривнях
        logger.info(
            "🔁 UAH rounding | "
            f"rate={usd_to_uah} UAH per USD, sale_raw={sale_price_usd_amt} USD ({q2(sale_price_uah)} UAH) "
            f"→ rounded_sale={sale_price_rounded_usd_amt} USD ({sale_price_rounded_uah} UAH), "
            f"round_delta={delta_uah} UAH, profit_rounded={profit_rounded_usd_amt} USD"
        )

        # === 🛡️ Meest insurance (percent of final price) ===
        # За замовчуванням фінальні значення збігаються з rounded
        sale_price_final_usd_amt = sale_price_rounded_usd_amt
        profit_final_usd_amt = profit_rounded_usd_amt

        if (
            self._cfg.meest_insurance_mode == "percent_final"
            and self._cfg.meest_insurance_percent > 0
        ):
            # 1) Страховка як % від уже округленої USD-ціни
            insurance_usd_amt = q2(
                sale_price_rounded_usd_amt * self._cfg.meest_insurance_percent / Decimal("100")
            )
            meest_insurance_amount_usd = insurance_usd_amt
            meest_insurance_percent = self._cfg.meest_insurance_percent

            # 2) Додаємо страховку та знову робимо маркетингове округлення через UAH
            sale_plus_insurance_usd = sale_price_rounded_usd_amt + insurance_usd_amt
            sale_plus_insurance_uah = sale_plus_insurance_usd * usd_to_uah
            sale_plus_insurance_uah_rounded = self._ceil_to_10_uah(q2(sale_plus_insurance_uah))

            sale_price_final_usd_amt = q2(sale_plus_insurance_uah_rounded / usd_to_uah)
            profit_final_usd_amt = q2(sale_price_final_usd_amt - cost_price_usd_amt)

            logger.info(
                "🛡️ Meest insurance (percent_final) | rate=%s%% → +%s USD; "
                "sale_rounded=%s USD → sale_final=%s USD (%s UAH)",
                self._cfg.meest_insurance_percent,
                insurance_usd_amt,
                sale_price_rounded_usd_amt,
                sale_price_final_usd_amt,
                sale_plus_insurance_uah_rounded,
            )

        # --- 📦 Крок 8: Пакуємо результат (строго Money-поля з Protocol) ---
        discounted_price_money = PMoney(discounted_price_usd, "USD")              # 💵 Підготовлена знижена ціна
        cost_without_delivery_money = PMoney(
            max(cost_without_delivery_usd_amt, Decimal("0")),
            "USD",
        )                                                                          # 📦 Собівартість без доставки (без негативів)
        result = FullPriceDetails(                                                 # 📦 Пакуємо агрегований результат
            sale_price=PMoney(sale_price_usd_amt, "USD"),
            # з урахуванням можливого percent_final
            sale_price_rounded=PMoney(sale_price_final_usd_amt, "USD"),
            base_price=PMoney(original_price_usd.amount, "USD"),
            cost_price=PMoney(cost_price_usd_amt, "USD"),
            profit=PMoney(profit_usd_amt, "USD"),
            profit_rounded=PMoney(profit_final_usd_amt, "USD"),
            full_delivery=PMoney(full_delivery_usd_amt, "USD"),
            protection=PMoney(protection_usd_amt, "USD"),
            discounted_price=discounted_price_money,
            meest_insurance=PMoney(meest_insurance_amount_usd, "USD"),
            meest_insurance_mode=meest_insurance_mode,
            meest_insurance_percent=meest_insurance_percent,
            discount_percent=self._cfg.discount_percent,
            local_delivery=local_delivery_usd,
            international_delivery=meest_delivery_money,
            cost_without_delivery=cost_without_delivery_money,
            markup=Decimal(str(final_markup)),
            markup_adjustment=markup_adjustment,
            weight_lbs=q2(weight_lbs),
            round_delta_uah=q2(delta_uah),
        )
        logger.info(
            "✅ Pricing completed | "
            f"sale_price={result.sale_price.amount} USD (rounded={result.sale_price_rounded.amount} USD) "
            f"cost_price={result.cost_price.amount} USD "
            f"profit={result.profit.amount} USD (rounded={result.profit_rounded.amount} USD) "
            f"markup={result.markup}% adjustment={result.markup_adjustment}% "
            f"round_delta={result.round_delta_uah} UAH"
        )
        return result                                                             # 📬 Повертаємо результат розрахунку

    # ==================================
    # 🧰 ПРИВАТНІ ЧИСТІ ДОПОМІЖНІ ФУНКЦІЇ
    # ==================================
    def _to_usd(self, money: PMoney, conv: IMoneyConverter) -> PMoney:
        """Адаптер під IMoneyConverter: PMoney(any) → PMoney(USD)."""
        if money.currency == "USD":                                    # ✅ Вже у потрібній валюті
            return PMoney(q2(money.amount), "USD")                     # 💵 Нормалізуємо та повертаємо USD
        converted = conv.convert_money(                                # 🔄 Конвертуємо через доменний конвертер
            CMoney(money.amount, CurrencyCode(money.currency)),
            CurrencyCode("USD"),
        )                                                               # 🏦 Отримуємо Decimal у USD
        return PMoney(q2(converted.amount), "USD")                     # 💵 Повертаємо нормалізований результат

    def _rate(self, conv: IMoneyConverter, amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal:
        """Отримати *amount* у `to_ccy` (Decimal), використовуючи convert_money()."""
        res = conv.convert_money(                                      # 🔄 Гроші у проміжному контейнері
            CMoney(amount, CurrencyCode(from_ccy)),
            CurrencyCode(to_ccy),
        )                                                               # 🏦 Результат у цільовій валюті
        return q2(res.amount)                                          # 📏 Повертаємо усічене значення

    @staticmethod
    def _lbs_to_grams(weight_lbs: Decimal) -> int:
        """1 lb = 453.59237 g → повертаємо ціле для тарифікації."""
        grams = (weight_lbs * Decimal("453.59237")).quantize(Decimal("1"))  # ⚖️ Конвертуємо фунти в грами
        return int(grams)                                              # 🔢 Повертаємо ціле значення грамів

    def _apply_discount(self, price_usd: Decimal) -> Decimal:
        """🎁 Застосовує фіксовану знижку магазину (cfg.discount_percent)."""
        return price_usd * (Decimal("1") - self._cfg.discount_percent / Decimal("100"))  # 🎯 Обчислюємо знижку

    @staticmethod
    def _navidium_cost(price_usd: Decimal) -> Decimal:
        """🛡️ Розраховує вартість страхування Navidium (ступінчасто)."""
        normalized_price = q2(price_usd)                               # 💵 Нормалізуємо вхідну суму
        if normalized_price <= Decimal("25.00"):                       # 🧮 Базовий щабель
            return Decimal("0.75")                                     # 🛡️ Мінімальна страховка
        if normalized_price <= Decimal("51.00"):                       # 🧮 Другий щабель тарифу
            return Decimal("1.50")                                     # 🛡️ Фіксований тариф
        base_premium = Decimal("1.50")                                 # 🛡️ Стартова сума після порогу
        amount_above_threshold = normalized_price - Decimal("51.00")   # 📈 Частина понад поріг
        step_count = Decimal(str(math.ceil(float(amount_above_threshold / Decimal("25.0")))))  # 🪜 Кількість кроків
        return base_premium + step_count * Decimal("0.75")             # 🛡️ Премія з урахуванням кроків

    @staticmethod
    def _final_markup(price_usd: Decimal, delivery_usd: Decimal) -> Tuple[Decimal, Decimal]:
        """📈 Базова націнка + коригування за часткою доставки."""
        price_usd_amount = price_usd                                   # 💵 Ціна товару як Decimal
        delivery_usd_amount = delivery_usd                             # 🚚 Доставка як Decimal
        combined_cost = price_usd_amount + delivery_usd_amount         # 🧮 Загальна база для частки

        if price_usd_amount < Decimal("20"):                           # 🧮 Діапазон ціни < 20
            base_markup_percent = Decimal("30")                        # 📈 Базова націнка
        elif price_usd_amount < Decimal("30"):                         # 🧮 20–30 USD
            base_markup_percent = Decimal("27")                        # 📈 Націнка для сегменту
        elif price_usd_amount < Decimal("40"):                         # 🧮 30–40 USD
            base_markup_percent = Decimal("25")                        # 📈 Відповідна ставка
        elif price_usd_amount < Decimal("50"):                         # 🧮 40–50 USD
            base_markup_percent = Decimal("23")                        # 📈 Зменшена ставка
        else:                                                          # 🧮 Більше 50 USD
            base_markup_percent = Decimal("20")                        # 📈 Мінімальна базова націнка

        delivery_share_percent = (delivery_usd_amount / combined_cost * Decimal("100")) if combined_cost > Decimal("0") else Decimal("0")  # 📊 Частка доставки
        if delivery_share_percent > Decimal("20"):                     # 🛫 Доставка занадто дорога
            adjustment_percent = Decimal("-3")                         # 🔻 Зменшуємо націнку
        elif delivery_share_percent < Decimal("10"):                   # 🛬 Доставка дешева
            adjustment_percent = Decimal("3")                          # 🔺 Збільшуємо націнку
        else:                                                          # ⚖️ Частка у комфортному коридорі
            adjustment_percent = Decimal("0")                          # ➖ Залишаємо без змін
        final_markup_percent = base_markup_percent + adjustment_percent  # 📈 Підсумкова націнка
        logger.info(
            "🧮 Markup rule | price=%s USD delivery=%s USD cost_share=%.2f%% base=%s%% adj=%s%% → final=%s%%",
            price_usd,
            delivery_usd,
            delivery_share_percent,
            base_markup_percent,
            adjustment_percent,
            final_markup_percent,
        )
        return final_markup_percent, adjustment_percent                # 📦 Повертаємо (markup, adjustment)

    @staticmethod
    def _ceil_to_10_uah(value_uah: Decimal) -> Decimal:
        """🔢 Округлює «вгору» до найближчих 10 грн (10, 20, 30, ...)."""
        tens = (value_uah // Decimal("10"))                            # 🔢 Базова кількість десятків
        needs_up = (value_uah % Decimal("10")) != 0                    # 🔄 Чи потрібне додаткове округлення
        return (tens + (1 if needs_up else 0)) * Decimal("10")         # 🔔 Повертаємо округлену суму
