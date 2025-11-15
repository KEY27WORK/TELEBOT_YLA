# 📦 app/infrastructure/delivery/meest_delivery_service.py
"""
📦 MeestDeliveryService — інфраструктурна реалізація доменного IDeliveryService.

Ключові рішення:
- Вага: вхід/вихід у грамах (int). Усередині переводимо в кг лише для правил.
- Гроші: Decimal (жодних float), квантовані до 2 знаків.
- Логіка tiers збережена повністю:
  • rate_per_kg (+ optional min_charge)
  • base_rate + rate_per_kg
  • only rate_per_kg
  • fixed_rate
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional

from app.config.config_service import ConfigService	# ⚙️ Сервіс конфігів
from app.domain.delivery import DeliveryQuote, IDeliveryService	# 📦 Доменні контракти

# ================================
# 🧾 ЛОГЕР
# ================================
logger = logging.getLogger(__name__)	# 🧾 Використовуємо модульний логер


class MeestDeliveryService(IDeliveryService):
    """
    🚚 Розрахунок вартості доставки Meest на основі tier‑правил з конфігурації.

    Очікуваний формат конфіга:
    delivery:
      meest:
        tariffs:
          ua:
            currency: "USD"
            tiers:
              - { max_kg: 0.5,  rate_per_kg: 12,  min_charge: 6 }
              - { max_kg: 5,    base_rate: 8,   rate_per_kg: 10 }
              - { max_kg: 20,   rate_per_kg: 9 }
              - { max_kg: 1000, fixed_rate: 200 }
    """

    def __init__(self, config_service: ConfigService) -> None:
        """⚙️ Завантажує тарифи Meest із конфігурації та валідуює їх."""
        tariffs = config_service.get("delivery.meest.tariffs", {})	# 🧾 Читаємо секцію тарифів
        if not isinstance(tariffs, dict) or not tariffs:
            logger.error("❗ Тарифи для Meest не знайдені або мають некоректний формат у config.yaml")
            raise ValueError("Тарифи для Meest не сконфігуровано.")
        self._tariffs: Dict[str, Any] = tariffs	# 📦 Зберігаємо тарифну таблицю
        logger.debug("📦 Завантажено тарифи Meest для країн: %s", list(tariffs.keys()))

    # ================================
    # 🧮 ПУБЛІЧНИЙ РОЗРАХУНОК ТАРИФУ
    # ================================
    def quote(
        self,
        *,
        country: str,
        method: str,
        type_: str,
        weight_g: int,
        volumetric_weight_g: Optional[int] = None,
    ) -> DeliveryQuote:
        """
        💸 Розрахувати вартість доставки.

        Returns:
            DeliveryQuote з Decimal‑ціною та тарифікованою вагою (г).
        """
        country_norm = (country or "").strip().lower()	# 🌍 Нормалізуємо країну
        method_norm = (method or "").strip().lower()	# ✈️ Метод доставки

        if method_norm != "air":
            raise ValueError(f"Непідтримуваний метод доставки: {method}. Доступний лише 'air'.")

        country_rules = self._tariffs.get(country_norm)	# 🔍 Витягуємо правила країни
        if not country_rules:	# 🚫 Немає даних для країни
            raise ValueError(f"Непідтримувана країна для доставки: {country_norm!r}")

        wg = int(weight_g or 0)	# ⚖️ Фактична вага
        vwg = int(volumetric_weight_g or 0)	# 🎈 Обʼємна вага
        calculation_weight_g = max(wg, vwg)	# 🧮 Беремо більшу
        if calculation_weight_g < 0:
            calculation_weight_g = 0	# 🛡️ Захищаємося від негативів

        weight_kg = self._to_decimal(calculation_weight_g) / Decimal("1000")	# 📏 Переводимо у кг

        price = self._calculate_price_by_tiers_kg(weight_kg=weight_kg, tiers=country_rules.get("tiers", []))	# 💸 Розрахунок
        price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)	# 💱 До копійок
        currency = str(country_rules.get("currency", "USD"))	# 💵 Валюта
        logger.info("💸 Meest quote: country=%s weight=%sg billed=%sg price=%s %s", country_norm, weight_g, calculation_weight_g, price, currency)

        return DeliveryQuote(
            price=price,
            currency=currency,
            service_code="meest",
            billed_weight_g=calculation_weight_g,
        )

    # ================================
    # 🧠 ВНУТРІШНЯ ЛОГІКА РОЗРАХУНКУ
    # ================================
    def _calculate_price_by_tiers_kg(self, *, weight_kg: Decimal, tiers: list) -> Decimal:
        """
        Застосовує перший підхожий tier. Підтримувані ключі:
        - max_kg (поріг, включно)
        - rate_per_kg
        - min_charge
        - base_rate
        - fixed_rate
        """
        for tier in tiers or []:	# 🔁 Перебираємо усі доступні пороги
            try:
                max_kg = self._to_decimal(tier.get("max_kg"))	# 📏 Максимальна вага для цього tier
            except Exception:
                logger.warning("⚠️ Пропущено tier через некоректний max_kg: %r", tier, exc_info=True)
                continue

            if weight_kg <= max_kg:
                logger.debug("📐 Застосовується tier %r для ваги %s кг.", tier, weight_kg)
                # 1) rate_per_kg + min_charge
                if "rate_per_kg" in tier and "min_charge" in tier:
                    rate = self._to_decimal(tier["rate_per_kg"])	# 💵 Тариф за кг
                    min_charge = self._to_decimal(tier["min_charge"])	# 📦 Мінімальний платіж
                    charge = rate * weight_kg	# 🧮 Розрахунок плати
                    return charge if charge >= min_charge else min_charge

                # 2) base_rate + rate_per_kg
                if "base_rate" in tier and "rate_per_kg" in tier:
                    base = self._to_decimal(tier["base_rate"])	# 💰 Базовий платіж
                    rate = self._to_decimal(tier["rate_per_kg"])	# 💵 Тариф за кг
                    return base + rate * weight_kg	# 🧮 База + змінна частина

                # 3) only rate_per_kg
                if "rate_per_kg" in tier:
                    rate = self._to_decimal(tier["rate_per_kg"])	# 💵 Єдина ставка
                    return rate * weight_kg	# 🧮 Розрахунок

                # 4) fixed_rate
                if "fixed_rate" in tier:
                    return self._to_decimal(tier["fixed_rate"])	# 💶 Фіксована ціна

                logger.warning("⚠️ Tier не містить відомих ключів: %r", tier)

        logger.warning("⚠️ Не знайдено підходящого тарифу для ваги %s кг. Повертається 0.", weight_kg)
        return Decimal("0")	# 🪣 Заглушка

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Надійна конвертація (int|float|str|Decimal) → Decimal."""
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as e:
            raise ValueError(f"Некоректне числове значення в тарифах: {value!r}") from e	# 🛑 Вказуємо на проблему
