# 🧩 Domain: availability

Чистий домен для логіки перевірки наявності товарів: **жодного I/O**, кешів чи мережі — лише трансформації переданих структур.

## Що всередині

```bash
📦 availability
┣ 📜 interfaces.py         # DTO + контракт сервісу
┣ 📜 services.py           # Реалізація доменного сервісу
┣ 📜 sorting_strategies.py # Гнучкі стратегії сортування розмірів
┗ 📜 status.py             # Enum AvailabilityStatus (YES / NO / UNKNOWN)
```

## Ключові ідеї

- **Тристановий статус** `AvailabilityStatus`: `YES`, `NO`, `UNKNOWN` — типобезпечно і без плутанини з `Optional[bool]`.
- **Чисті DTO**: `RegionStock`, `AvailabilityReport` — frozen/slots для компактності та передбачуваності.
- **Інʼєкція стратегії сортування розмірів** — легко змінити порядок без правок бізнес‑логіки.
- **Детермінований порядок** у звітах — стабільні логи/тести.

## Публічні типи

- `RegionStock`: карта наявності в одному регіоні:
  ```py
  RegionStock(
      region_code="us",
      stock_data={
          "Black": {"S": YES, "M": NO, "L": UNKNOWN},
          "White": {"M": YES},
      },
  )
  ```

- `AvailabilityReport` — агрегований звіт:

    ```py
    AvailabilityReport(
        availability_by_region={  # де доступно (YES) по регіонах
            "Black": {"us": ["S"], "eu": ["M", "L"]},
        },
        all_sizes_map={           # усі відомі розміри по кольору (для рядків/таблиць)
            "Black": ["S", "M", "L"],
        },
        merged_stock={            # зведений статус по всіх регіонах
            "Black": {"S": YES, "M": NO, "L": UNKNOWN},
        },
    )
    ```

## Швидкий старт
    ```py
        from app.domain.availability.interfaces import RegionStock
        from app.domain.availability.services import AvailabilityService
        from app.domain.availability.status import AvailabilityStatus as AS

        # 1) Сирові дані з парсерів по регіонах (вже enum, не bool)
        regions = [
            RegionStock(
                region_code="us",
                stock_data={"Black": {"S": AS.YES, "M": AS.NO}}
            ),
            RegionStock(
                region_code="eu",
                stock_data={"Black": {"M": AS.YES, "L": AS.UNKNOWN}}
            ),
        ]

        # 2) Доменний сервіс (чистий, без I/O)
        service = AvailabilityService()

        # 3) Створити агрегований звіт
        report = service.create_report(regions)

        print(report.availability_by_region)  # {'Black': {'eu': ['M'], 'us': ['S']}}
        print(report.all_sizes_map)           # {'Black': ['S', 'M', 'L']}
        print(report.merged_stock)            # {'Black': {'S': YES, 'M': YES, 'L': UNKNOWN}}
    ```

Примітка: у прикладі merged_stock['Black']['M'] == YES, бо хоча в US M = NO, в EU M = YES → правило YES має пріоритет.

## Сортування розмірів

За замовчуванням використовується стратегія default_size_sort_key:
	1.	Відомі літерні розміри у порядку XXXS..XXXL
	2.	Числові (включно з дробами 42.5/42,5) за зростанням
	3.	Інше — лексикографічно

# Можна підмінити:
```py
from app.domain.availability.services import AvailabilityService
from app.domain.availability.sorting_strategies import default_size_sort_key

service = AvailabilityService()
report = service.create_report(regions, size_key=default_size_sort_key)
```

# Або передати власний ключ:
```py
def my_sort_key(size: str) -> tuple[int, int, str]:
    # приклад: всі XL спочатку
    s = (size or "").strip().upper()
    return (0, 0, "") if s == "XL" else (1, 0, s)

report = service.create_report(regions, size_key=my_sort_key)
```

## Поведінкові правила (зведення статусів)
Для кожного (color, size) по всіх регіонах:
	•	якщо є хоча б один YES → YES
	•	інакше, якщо є хоча б один NO → NO
	•	інакше → UNKNOWN

## Тестування (мінімальний набір)
	•	AvailabilityStatus:
	•	from_bool, from_str, merge, combine, priority, emoji, to_bool
	•	AvailabilityService._group_data:
	•	коректне наповнення availability_by_region і all_sizes_map
	•	AvailabilityService._merge_stock:
	•	пріоритети YES > NO > UNKNOWN, стабільне сортування ключем
	•	create_report:
	•	інтеграційно з різними наборами регіонів/розмірів/стратегій

## Залежності

Цей пакет не має залежностей на інфраструктуру (бот, парсери, кеш).
Він імпортується інфраструктурою і працює лише з переданими структурами.

⸻