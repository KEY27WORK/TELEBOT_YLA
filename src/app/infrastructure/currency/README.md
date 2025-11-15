# 💱 Currency Infrastructure

Стек для Decimal-first конвертації валют, кешування курсів та видачі snapshot-конвертерів.

---

## 📂 Структура
```bash
currency/
├── 📘 README.md                 # (цей файл) путівник каталогу
├── 📄 __init__.py               # експортує CurrencyManager/CurrencyConverter
├── 📄 currency_converter.py     # чистий синхронний конвертер (Decimal + float API)
├── 📄 currency_manager.py       # асинхронний менеджер курсів (Monobank, кеш, TTL)
└── 📄 current_rate.txt          # кешовані курси у JSON-форматі
```

---

## 🧭 Призначення
- Забезпечити точну Decimal-конвертацію (`IMoneyConverter`) та сумісність із float API (`ICurrencyConverter`).
- Асинхронно отримувати курси з Monobank, додавати маржу, кешувати у файлі та оновлювати за TTL.
- Створювати snapshot-конвертери, щоб бізнес-логіка працювала зі стабільним станом курсів.
- Дозволяти ручний override курсів (наприклад, у випадку аварій чи дев-режиму).

---

## 🧱 Ключові файли
- **`currency_converter.py`**
  - `CurrencyConverter` реалізує `IMoneyConverter` (Decimal API) і `ICurrencyConverter` (legacy float API).
  - Внутрішньо працює лише з Decimal, float повертається лише на межі.
  - Підтримує параметризовану стратегію округлення (за замовчуванням `ROUND_HALF_EVEN`).

- **`currency_manager.py`**
  - `CurrencyManager` асинхронно тягне курси (Monobank), додає маржу, кешує у `current_rate.txt`.
  - Надає методи `get_money_converter()` та `get_converter()` для отримання snapshot-конвертерів.
  - Вміє оновлювати курси за TTL (`update_all_rates_if_needed`) або примусово (`update_all_rates`), а також встановлювати курс вручну.

- **`current_rate.txt`**
  - JSON-файл із кешованими курсами (значення зберігаються як числа/рядки, наприклад `{"USD": 42.69, "UAH": 1.0}`).
  - Використовується як cold-start fallback або для ручних правок.

---

## 🚀 Приклад використання
```python
from app.config.config_service import ConfigService
from app.infrastructure.currency import CurrencyManager

config = ConfigService()
currency_manager = CurrencyManager(config)

await currency_manager.initialize()
await currency_manager.update_all_rates_if_needed()

money_converter = currency_manager.get_money_converter()  # точний Decimal API
legacy_converter = currency_manager.get_converter()       # legacy float API
```

---

## ⚙️ Налаштування (config)
```yaml
currency_api:
  url: "https://api.monobank.ua/bank/currency"
  codes:
    USD: 840
    EUR: 978
    GBP: 826
    PLN: 985
  margin: 0.5                     # додається до курсу перед квантовкою
  timeout_sec: 5
  retry_attempts: 2
  retry_delay_sec: 2
  ttl_sec: 600
  fallback_rates:
    USD: "42.69"
    EUR: "49.99"
    GBP: "58.04"
    PLN: "12.15"
files:
  currency_rates: "current_rate.txt"
```

---

## ✅ Примітки
- Усі внутрішні обчислення — Decimal; float пересічний тільки на legacy API.
- Квант курсів у файлі/пам’яті: 4 знаки після коми (`Decimal("0.0001")`).
- `__init__.py` експортує `CurrencyManager` та `CurrencyConverter`, тож імпорт виглядає як `from app.infrastructure.currency import CurrencyManager`.
- Файл `current_rate.txt` оновлюється автоматично після кожного успішного оновлення або ручної зміни курсу.
