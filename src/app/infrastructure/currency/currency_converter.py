# 💱 app/infrastructure/currency/currency_converter.py
"""
💱 Stateless-конвертер, що працює з «снімком» валютних курсів у Decimal.

🔹 Реалізує `IMoneyConverter` (точне Decimal API) та `ICurrencyConverter` (legacy float API).
🔹 Підтримує параметризовану стратегію округлення (за замовчуванням ROUND_HALF_EVEN).
🔹 Логує ключові етапи: ініціалізацію контексту, квантовані обчислення та конверсії.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування всіх операцій
from dataclasses import dataclass										# 🧱 Контекст для immutable стану
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation			# 💰 Точна арифметика та округлення
from typing import Dict, Mapping, Union									# 📐 Підтримка гнучких типів курсів

# 🧩 Внутрішні модулі проєкту
from app.domain.currency.interfaces import (							# 🔗 Контракти домену
    CurrencyCode,
    CurrencyRateNotFoundError,
    ICurrencyConverter,
    IMoneyConverter,
    Money,
)
from app.shared.utils.logger import LOG_NAME							# 🏷️ Єдине імʼя логера


# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)									# 🧾 Модульний логер


# ================================
# 📏 НАЛАШТУВАННЯ КВАНТУВАННЯ
# ================================
_CCY_DECIMALS: Dict[str, int] = {
    "UAH": 2,															# 🇺🇦 Гривня
    "USD": 2,															# 🇺🇸 Долар
    "EUR": 2,															# 🇪🇺 Євро
    "GBP": 2,															# 🇬🇧 Фунт
    "PLN": 2,															# 🇵🇱 Злотий
}


# ================================
# 🧰 ДОПОМІЖНІ ФУНКЦІЇ
# ================================
def _to_decimal(value: object) -> Decimal:
    """🧮 Безпечно приводить значення до Decimal через рядкове представлення."""
    if isinstance(value, Decimal):
        return value
    try:
        normalized = Decimal(str(value).strip())						# 🧼 Позбавляємося артефактів float
        logger.debug("🔢 _to_decimal: %r → %s", value, normalized)
        return normalized
    except (InvalidOperation, AttributeError, ValueError) as exc:
        logger.error("❌ Неможливо привести до Decimal: %r", value, exc_info=True)
        raise ValueError(f"Невалідне числове значення: {value!r}") from exc


def _quantum_for_currency(currency: str) -> Decimal:
    """📏 Обчислює квантування (10^-digits) для валюти."""
    digits = _CCY_DECIMALS.get(currency.upper(), 2)						# 🔢 Кількість десяткових знаків
    quantum = Decimal(1).scaleb(-digits)									# 📐 10^-digits
    logger.debug("📏 Quantum для %s = %s", currency, quantum)
    return quantum


def _quantize(amount: Decimal, currency: str, rounding: str) -> Decimal:
    """📐 Квантоване значення з урахуванням валюти та стратегії округлення."""
    quantized = amount.quantize(_quantum_for_currency(currency), rounding=rounding)
    logger.debug("📐 Квантовано %s %s → %s (rounding=%s)", amount, currency, quantized, rounding)
    return quantized


# ================================
# ⚙️ КОНТЕКСТ ВИКОНАННЯ
# ================================
@dataclass(frozen=True)
class _Ctx:
    """⚙️ Контекст обчислень: курси та стратегія округлення."""

    rates: Dict[str, Decimal]											# 💱 Курси вигляду {"USD": Decimal(...)}
    rounding: str														# 🔁 Стратегія округлення (ROUND_* constant)


# ================================
# 💱 КОНВЕРТЕР
# ================================
class CurrencyConverter(ICurrencyConverter, IMoneyConverter):
    """
    💱 Синхронний конвертер на базі знімка курсів у Decimal.

    - Внутрішньо працює **лише** з Decimal.
    - Легасі-метод `convert(float, …)` понижує точність на межі, щоби зберегти API.
    """

    _ctx: _Ctx															# 🧱 Поточний контекст конвертації

    # ================================
    # 🏗️ ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        rates: Mapping[str, Union[Decimal, int, float, str]],
        *,
        rounding: str = ROUND_HALF_EVEN,
    ) -> None:
        if not isinstance(rates, Mapping):
            raise TypeError("rates повинен бути Mapping[str, Decimal|int|float|str].")

        normalized: Dict[str, Decimal] = {}								# 📦 Сюди зберемо нормалізовані курси
        for key, value in (rates or {}).items():
            currency = (key or "").upper().strip()						# 🧭 Вирівнюємо код валюти
            if not currency:
                continue
            normalized[currency] = _to_decimal(value)					# 💱 Конвертуємо курс у Decimal
            logger.debug("💾 Курс %s = %s", currency, normalized[currency])

        if "UAH" not in normalized:										# 🇺🇦 Гарантуємо наявність базової валюти
            normalized["UAH"] = Decimal("1")
            logger.info("ℹ️ Додано базову валюту UAH зі значенням 1.")

        context = _Ctx(rates=normalized, rounding=rounding)				# ⚙️ Створюємо контекст
        object.__setattr__(self, "_ctx", context)						# 📌 Зберігаємо у frozen dataclass
        logger.info("💱 CurrencyConverter готовий (валют: %d, rounding=%s)", len(normalized), rounding)

    # ================================
    # 🧮 ДОПОМІЖНА ТОЧНА КОНВЕРТАЦІЯ
    # ================================
    def _convert_decimal(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """🧮 Конвертує Decimal між валютами з урахуванням курсів та округлення."""
        from_ccy = (from_currency or "").upper()						# 🔁 Валюта-джерело
        to_ccy = (to_currency or "").upper()							# 🎯 Валюта призначення
        logger.debug("🔄 _convert_decimal: %s %s → %s", amount, from_ccy, to_ccy)

        if from_ccy == to_ccy:
            logger.debug("🔁 Валюти збігаються, лишень квантую результат.")
            return _quantize(amount, to_ccy, self._ctx.rounding)

        try:
            from_rate_to_uah = self._ctx.rates[from_ccy]				# 📈 Курс джерела до базової
            to_rate_from_uah = self._ctx.rates[to_ccy]					# 📉 Курс базової до цілі
        except KeyError as missing:
            logger.error("❌ Відсутній курс для %s → %s", from_ccy, to_ccy, exc_info=True)
            raise CurrencyRateNotFoundError(from_ccy, to_ccy) from missing

        if to_rate_from_uah == 0:
            logger.error("❌ Курс для %s дорівнює нулю", to_ccy)
            raise ValueError(f"Нульовий курс для валюты: {to_ccy}")

        amount_in_base = amount * from_rate_to_uah						# 💵 Переводимо у базову валюту
        dest_amount = amount_in_base / to_rate_from_uah					# 💵 Конвертуємо в цільову
        result = _quantize(dest_amount, to_ccy, self._ctx.rounding)		# 📐 Застосовуємо округлення
        logger.debug(
            "✅ Конвертовано %s %s → %s %s (from_rate=%s, to_rate=%s)",
            amount,
            from_ccy,
            result,
            to_ccy,
            from_rate_to_uah,
            to_rate_from_uah,
        )
        return result

    # ================================
    # 💵 API ДЛЯ Money (Decimal)
    # ================================
    def convert_money(self, money: Money, to_currency: CurrencyCode) -> Money:
        """💵 Конвертує доменний `Money` у задану валюту."""
        amount_dec = _to_decimal(money.amount)							# 💰 Приводимо суму до Decimal
        to_ccy = str(to_currency).upper()								# 🎯 Призначення
        result = self._convert_decimal(amount_dec, str(money.currency), to_ccy)
        logger.info(
            "💵 convert_money: %s %s → %s %s",
            money.amount,
            money.currency,
            result,
            to_ccy,
        )
        return Money(amount=result, currency=CurrencyCode(to_ccy))		# 📦 Повертаємо новий Money

    # ================================
    # 🧮 LEGACY API (float)
    # ================================
    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """🧮 Зворотна сумісність: конвертує float на вході/виході, всередині працює з Decimal."""
        amount_dec = _to_decimal(amount)									# 💰 Перетворюємо у Decimal
        result_dec = self._convert_decimal(amount_dec, from_currency, to_currency)
        result = float(result_dec)										# 🔻 Повертаємо float
        logger.info(
            "🧮 convert(float): %.4f %s → %.4f %s",
            amount,
            from_currency,
            result,
            to_currency,
        )
        return result
