app/domain/delivery/README.md
# 🚚 Delivery Domain

Доменно‑орієнтований модуль для **розрахунку вартості доставки**. Містить лише
чисті контракти та DTO — без залежностей від інфраструктури.

## 🎯 Призначення

- **DTO**: `DeliveryQuote` (ціна, валюта, сервіс, тарифікована вага).
- **Контракт**: `IDeliveryService.quote(...) → DeliveryQuote`.
- Жодної мережевої роботи у `__init__`. Винятки не «ковтаються».

## 🧱 Інваріанти

- **Гроші**: тільки `Decimal` (жодних `float`).
- **Вага**: тільки **грами** (`int`) для вхідних аргументів і для `billed_weight_g`.
- **Ідемпотентність**: однакові аргументи → однаковий результат.

## 📂 Структура

```bash
domain/delivery/
├── 📘 README.md
├── __init__.py            # Реекспорт -> DeliveryQuote, IDeliveryService
└── interfaces.py          # DTO + контракт для розрахунку доставки
```

## 📦 Публічні API

```python
from app.domain.delivery import IDeliveryService, DeliveryQuote
DeliveryQuote
price: Decimal — підсумкова ціна
currency: str — код валюти (напр., "USD")
service_code: str — код провайдера/тарифу (напр., "meest")
billed_weight_g: int — тарифікована вага у грамах
IDeliveryService
def quote(
    *,
    country: str,                 # "UA", "PL", ...
    method: str,                   # "air" | "ground" | "express" | ...
    type_: str,                    # "parcel" | "letter" | ...
    weight_g: int,                 # фактична вага, г
    volumetric_weight_g: int | None = None  # об'ємна, якщо застосовується
) -> DeliveryQuote: ...
```

##  🚀 Приклад використання

```python
from decimal import Decimal
from app.domain.delivery import IDeliveryService

def format_quote(service: IDeliveryService) -> str:
    quote = service.quote(
        country="UA",
        method="air",
        type_="parcel",
        weight_g=850,                 # 0.85 кг
        volumetric_weight_g=None,
    )
    return f"{quote.service_code}: {quote.price} {quote.currency} за {quote.billed_weight_g} г"

```

##  ✅ Якість
Чистий домен: без http‑клієнтів, SDK чи побічних ефектів у конструкторах.
Докстрінги, типи та інваріанти — обовʼязкові.





