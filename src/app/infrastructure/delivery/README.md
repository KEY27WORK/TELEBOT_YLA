# 🚚 Delivery Infrastructure

Інфраструктурний шар для **реальних реалізацій сервісів доставки**, які
імплементують доменний контракт [`IDeliveryService`](../../domain/delivery/interfaces.py).

---

## 📂 Вміст
```bash
delivery/
├── 📘 README.md              # (цей файл)
├── 📄 __init__.py            # експортує MeestDeliveryService
└── 📄 meest_delivery_service.py  # реалізація IDeliveryService для Meest
```

---

## 🧭 Призначення

- Тут розташовуються **конкретні провайдери доставки** (Meest, NovaPoshta, DHL…).
- Вони використовують **чистий контракт домену** `IDeliveryService`.
- Логіка тарифів ізолюється й читається з конфігів, а не зашивається в код.

---

## 🚀 Приклад використання

```python
from app.config.config_service import ConfigService
from app.infrastructure.delivery import MeestDeliveryService

config = ConfigService("config.yaml")
delivery_service = MeestDeliveryService(config)

quote = delivery_service.quote(
    country="UA",
    method="air",
    type_="parcel",
    weight_g=850,
    volumetric_weight_g=None,
)

print(f"{quote.service_code}: {quote.price} {quote.currency} за {quote.billed_weight_g} г")
```

## ✅ Стиль / гарантії
	•	Вага — грами (int).
	•	Гроші — Decimal (жодних float).
	•	Жодних сторонніх HTTP-клієнтів у цьому шарі — лише бізнес-логіка на базі даних із конфігів.
