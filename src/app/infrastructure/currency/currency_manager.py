# 💵 app/infrastructure/currency/currency_manager.py
"""
💵 CurrencyManager — інфраструктурний сервіс життєвого циклу валютних курсів.

🔁 Decimal-first staged rollout:
    • внутрішньо всі курси зберігаються як Decimal (UAH за одиницю валюти);
    • публічні геттери повертають snapshot-конвертери (`IMoneyConverter` та `ICurrencyConverter`).

🎯 Призначення:
    • асинхронно отримує курси з Monobank, кешує та оновлює їх за TTL;
    • зберігає резервні копії на диску й у разі потреби дозволяє ручне встановлення курсу;
    • будує `CurrencyConverter` з потрібною стратегією округлення (ROUND_HALF_EVEN).

⚙️ Нотатки:
    • квант курсів у кеші/файлі — 4 знаки після коми (стабільні порівняння, читабельний JSON);
    • усі методи супроводжуються докладним логуванням, щоб спростити діагностику.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import aiofiles                                                     # 💽 Асинхронна робота з файлами
import httpx                                                        # 🌐 HTTP-клієнт для Monobank

# 🔠 Системні імпорти
import asyncio                                                      # 🔁 Асинхронні операції/локи
import json                                                         # 📄 Серіалізація кешу курсів
import logging                                                      # 🧾 Логи сервісу
import time                                                         # ⏱️ TTL/мітки часу
from decimal import Decimal, ROUND_HALF_EVEN                        # 💰 Аритметика й округлення
from typing import Any, Dict, List, Optional, Protocol, Union, cast # 📐 Типізація публічних методів

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                  # ⚙️ Конфіги застосунку
from app.domain.currency.interfaces import ICurrencyConverter, IMoneyConverter

# 🏦 Доменні інтерфейси конвертерів валют

# 🛟 Fallback-протокол для сумісності з різними версіями доменних інтерфейсів
try:  # pragma: no cover
    from app.domain.currency.interfaces import ICurrencyRatesProvider  # type: ignore  # 🔗 Прагнемо використовувати офіційний інтерфейс
except Exception:  # pragma: no cover
    class ICurrencyRatesProvider(Protocol):  # noqa: N801
        async def initialize(self) -> None: ...              # 🚀 Ініціалізація провайдера курсів
        async def close(self) -> None: ...                   # 🧹 Закриття ресурсу
        def get_money_converter(self) -> IMoneyConverter: ...        # 🔁 Конвертер Money → Money
        def get_converter(self) -> ICurrencyConverter: ...           # 🔁 Легасі-конвертер float → float
        def get_all_rates(self) -> Dict[str, Decimal]: ...           # 💱 Усі курси у вигляді словника
        @property
        def last_update_ts(self) -> float: ...                       # ⏱️ Timestamp останнього оновлення
        def is_cache_fresh(self) -> bool: ...                        # ♻️ Перевірка актуальності кешу

from app.infrastructure.currency.currency_converter import CurrencyConverter   # 🔧 Локальний конвертер валют
from app.shared.utils.logger import LOG_NAME                                  # 🏷️ Ім'я централізованого логера

logger = logging.getLogger(LOG_NAME)                                          # 🧾 Модульний логер


class CurrencyManager(ICurrencyRatesProvider):
    """
    🏦 Керує життєвим циклом курсів валют і надає конвертери (знімки стану).
    """

    _UAH_CODE = 980  # ISO-код UAH у відповіді Monobank
    _RATE_QUANTUM = Decimal("0.0001")  # квант збереження/порівняння курсів
    _ROUNDING = ROUND_HALF_EVEN        # стратегія округлення (BANKERS)

    def __init__(self, config_service: ConfigService) -> None:
        self._config = config_service                                # ⚙️ Джерело конфігів
        self._lock = asyncio.Lock()                                  # 🔐 Захист оновлення курсів

        # ── Параметри з конфігів ────────────────────────────────────────────
        _api_url = self._config.get("currency_api.url")             # 🌐 Endpoint Monobank
        _rate_file_path = self._config.get("files.currency_rates")  # 💾 Шлях до кеш-файлу
        if not _api_url or not isinstance(_api_url, str):
            raise ValueError("Config 'currency_api.url' is required and must be str.")
        if not _rate_file_path or not isinstance(_rate_file_path, str):
            raise ValueError("Config 'files.currency_rates' is required and must be str.")

        self._api_url: str = cast(str, _api_url)                     # 🌐 Перевірений URL API
        self._rate_file_path: str = cast(str, _rate_file_path)       # 💾 Шлях до кешу

        self._currency_codes: Dict[str, int] = cast(
            Dict[str, int], self._config.get("currency_api.codes", {}) or {}
        )                                                            # 📖 Мапа валют → їхні ISO-коди
        self._margin_raw: Union[float, int, str] = cast(
            Union[float, int, str], self._config.get("currency_api.margin", 0.5)
        )                                                            # 💸 Сира маржа (float/int/str) з конфігів
        self._timeout: int = cast(int, self._config.get("currency_api.timeout_sec", 5) or 5)      # ⏱️ Таймаут HTTP
        self._retries: int = cast(int, self._config.get("currency_api.retry_attempts", 2) or 2)   # 🔁 Кількість спроб
        self._retry_delay: int = cast(int, self._config.get("currency_api.retry_delay_sec", 2) or 2)  # 💤 Пауза між спробами
        self._min_ttl_sec: int = cast(int, self._config.get("currency_api.ttl_sec", 600) or 600)  # 🧭 Мінімальний TTL кешу

        # ── Стан ────────────────────────────────────────────────────────────
        self._rates: Dict[str, Decimal] = {}                         # 💱 Поточні курси (UAH за одиницю)
        self._client: Optional[httpx.AsyncClient] = None             # 🌐 HTTP-клієнт Monobank
        self._last_update_ts: float = 0.0                            # 🕒 Час останнього оновлення
        self._init_lock = asyncio.Lock()                             # 🔐 Послідовна ініціалізація
        logger.debug(
            "⚙️ CurrencyManager config: url=%s file=%s margin=%s ttl=%s",
            self._api_url,
            self._rate_file_path,
            self._margin_raw,
            self._min_ttl_sec,
        )

    # ================================
    # 🔓 ПУБЛІЧНИЙ ІНТЕРФЕЙС
    # ================================
    def get_money_converter(self) -> IMoneyConverter:
        """
        Повертає точний Decimal-конвертер як знімок поточного стану курсів.

        Використання:
            • фінансова логіка, де важлива Decimal-точність без проміжних float;
            • фіксація snapshot-стану курсів на момент розрахунку.
        """
        snapshot = self._rates.copy()                                # 🧾 Локальна копія словника курсів (іммутабельний snapshot)
        logger.debug("💾 Створено Decimal-конвертер зі станом: %s", snapshot)
        # 🔄 CurrencyConverter працює поверх переданого snapshot і не мутує _rates напряму
        return CurrencyConverter(snapshot, rounding=self._ROUNDING)

    def get_converter(self) -> ICurrencyConverter:
        """
        Повертає легасі-конвертер (float API) як знімок поточного стану курсів.

        Точність усередині — Decimal, але:
            • інтерфейс може очікувати float;
            • підходить для сумісності з існуючим кодом, який не вміє працювати з Decimal.
        """
        snapshot = self._rates.copy()                                # 🧾 Так само фіксуємо стан курсов на момент виклику
        logger.debug("💾 Створено legacy-конвертер зі станом: %s", snapshot)
        return CurrencyConverter(snapshot, rounding=self._ROUNDING)

    def get_all_rates(self) -> Dict[str, Decimal]:
        """
        Повертає копію актуальних курсів у вигляді:
            { "USD": Decimal("40.5000"), "EUR": Decimal("43.1000"), ... }

        Важливо:
            • повертається копія, а не посилання на внутрішній стан;
            • зовнішній код не може випадково зламати _rates.
        """
        return self._rates.copy()                                    # 📤 Повертаємо копію, аби зовнішній код не мутував стан

    @property
    def last_update_ts(self) -> float:
        """
        Unix-час останнього успішного оновлення кешу курсів.

        Може використовуватись:
            • для діагностики (через /debug або метрики);
            • для ручної перевірки "наскільки свіжі" курси.
        """
        return self._last_update_ts                                  # 🕒 Повертаємо timestamp як є

    def is_cache_fresh(self) -> bool:
        """
        True, якщо TTL кешу ще не минув (оновлення поки не потрібне).

        Логіка:
            • беремо поточний час;
            • віднімаємо last_update_ts;
            • якщо різниця менша за TTL — кеш вважаємо свіжим.
        """
        return (time.time() - self._last_update_ts) < max(0, int(self._min_ttl_sec or 0))  # ✅ True якщо різниця < TTL

    async def initialize(self) -> None:
        """
        Ініціалізує кеш курсів з диску та створює HTTP-клієнт.

        Викликається:
            • один раз на старті сервісу;
            • або ледачо через ensure_initialized().
        """
        async with self._init_lock:                                  # 🔐 Захист від паралельного multi-init
            if not self._rates:
                # 🔄 Пробуємо підтягнути кешовані курси з файлу або fallback з конфігів
                self._rates = await self._load_rates_from_file()
            if not self._client:
                # 🌐 Ініціалізуємо HTTP-клієнт з таймаутом з конфігів
                self._client = httpx.AsyncClient(timeout=self._timeout)
                logger.info("🔧 CurrencyManager ініціалізовано з курсами: %s", self._rates)

    async def ensure_initialized(self) -> None:
        """
        Гарантує, що кеш курсів підготовлений та HTTP-клієнт створений.

        Швидка перевірка:
            • якщо _client вже є та _rates не порожні — просто повертаємося;
            • інакше викликаємо повну initialize().
        """
        if self._client and self._rates:
            return                                                  # 🟢 Уже повністю ініціалізовано
        await self.initialize()                                     # 🚀 Піднімаємо все з нуля

    async def close(self) -> None:
        """
        Акуратно закриває HTTP-клієнт.

        Викликати:
            • при graceful shutdown сервісу;
            • щоб не залишати відкриті TCP-зʼєднання.
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("🔌 HTTP-клієнт менеджера валют закрито.")

    async def update_all_rates_if_needed(self) -> None:
        """
        🔄 Оновлює курси тільки якщо минув TTL (умовне оновлення).

        Алгоритм:
            1. Переконуємося, що сервіс ініціалізований.
            2. Якщо кеш свіжий — лог і вихід.
            3. Якщо TTL вичерпано — викликаємо примусове оновлення.
        """
        await self.ensure_initialized()
        if self.is_cache_fresh():
            logger.debug("⏱️ Курси свіжі (TTL). Оновлення пропущено.")
            return
        logger.info("⏰ TTL вичерпано — запускаю оновлення курсів…")
        await self.update_all_rates()

    async def update_all_rates(self) -> None:
        """
        🔄 Примусово оновлює всі курси з API та оновлює last_update_ts.

        Особливості:
            • робить HTTP-запит до API;
            • обробляє сирі дані;
            • при змінах — зберігає кеш у файл.
        """
        await self.ensure_initialized()
        api_data = await self._fetch_api_data()
        if api_data is None:
            # ❗ Якщо API недоступне / повернуло некоректний формат — зберігаємо старі курси
            logger.warning("⚠️ Не вдалося отримати дані від API, оновлення курсів скасовано.")
            return

        async with self._lock:                                      # 🔐 Серіалізація оновлення курсів
            was_updated = self._process_api_data(api_data)
            if was_updated:
                # 💾 Записуємо нові значення в кеш-файл тільки якщо щось реально змінилося
                await self._save_rates_to_file()
            self._last_update_ts = time.time()                       # 🕒 Фіксуємо час оновлення незалежно від змін
            logger.info("🕒 Курси оновлено, last_update_ts=%s", self._last_update_ts)

    async def set_rate_manually(self, currency: str, rate: Union[Decimal, float, int, str]) -> None:
        """
        ✍️ Ручна установка курсу конкретної валюти (UAH за 1 одиницю).

        Параметри:
            currency:
                • код валюти (USD, EUR, ...), регістр не важливий;
            rate:
                • числове значення (Decimal/float/int/str), яке буде безпечно
                  приведено до Decimal та квантовано.

        Використовується для:
            • ручної корекції курсів адміністратором;
            • аварійних сценаріїв, коли API тимчасово недоступне.
        """
        await self.ensure_initialized()
        safe_rate = self._to_decimal(rate)                           # 🔢 Нормалізація типу до Decimal
        if safe_rate <= 0:
            logger.error("🚫 Спроба встановити невалідний курс для %s: %r", currency, rate)
            raise ValueError("Невалідний курс (повинен бути > 0).")

        ccy = (currency or "").upper().strip()                       # 🔤 Нормалізація коду валюти
        if not ccy:
            raise ValueError("Порожній код валюти.")

        async with self._lock:
            # 📏 Зберігаємо вже квантоване значення (4 знаки після коми)
            self._rates[ccy] = self._quantize_rate(safe_rate)
            await self._save_rates_to_file()
            self._last_update_ts = time.time()                       # 🕒 Фіксуємо час ручного оновлення
            logger.info("✍️ Курс для %s встановлено вручну: %s", ccy, self._rates[ccy])

    # ================================
    # 🔒 ВНУТРІШНЯ ЛОГІКА
    # ================================
    def _process_api_data(self, api_data: List[Dict[str, Any]]) -> bool:
        """
        Обробляє сирі дані Monobank і оновлює внутрішню мапу курсів по заданих кодах.

        Повертає:
            True — якщо був змінений хоча б один курс;
            False — якщо всі курси залишилися без змін.

        Правило оновлення:
            • якщо новий курс > старого (або старий <= 0) — оновлюємо;
            • менший/такий самий курс не зменшує вже встановлене значення.
        """
        was_updated = False                                            # 🔁 Чи змінився хоч один курс
        margin = self._to_decimal(self._margin_raw)                    # 💸 Маржа (націнка) з конфігів
        logger.debug("📊 Обробка API даних: margin=%s", margin)

        for currency_name, currency_code in self._currency_codes.items():
            # 🔍 Шукаємо потрібну пару: (valuta → UAH)
            entry = self._find_pair(api_data, a=currency_code, b=self._UAH_CODE)
            if not entry:
                logger.debug("🔍 Не знайдено пару для %s (code=%s)", currency_name, currency_code)
                continue

            # 🧮 Беремо rateSell, якщо немає — rateCross, далі — rateBuy
            raw_rate = entry.get("rateSell") or entry.get("rateCross") or entry.get("rateBuy")
            if raw_rate is None:
                # ❗ Якщо в записі немає жодного з очікуваних полів — пропускаємо
                continue

            try:
                base_rate = self._to_decimal(raw_rate)                # 💰 Базовий курс з API (Decimal)
                new_rate = self._quantize_rate(base_rate + margin)   # ➕ Додаємо маржу й квантуємо
            except (ValueError, TypeError):
                logger.warning("⚠️ Неможливо конвертувати курс: %r", raw_rate)
                continue

            old_rate = self._rates.get(currency_name, Decimal("0"))   # 📥 Поточне значення з кешу
            if new_rate > old_rate or old_rate <= 0:
                # 🔺 Оновлюємо тільки в кращу сторону (або при відсутності валідного значення)
                logger.info(
                    "🔺 Курс %s оновлено: %s → %s (margin=%s)",
                    currency_name,
                    old_rate,
                    new_rate,
                    margin,
                )
                self._rates[currency_name] = new_rate
                was_updated = True
            else:
                # 🔹 Курс не погіршився — залишаємо старе значення
                logger.debug("🔹 Курс %s залишився без змін: %s", currency_name, old_rate)

        return was_updated

    def _find_pair(self, api_data: List[Dict[str, Any]], a: int, b: int) -> Optional[Dict[str, Any]]:
        """
        Повертає перший запис з пари (currencyCodeA=a, currencyCodeB=b).

        Використовується:
            • щоб знайти потрібну валютну пару в масиві відповідей API;
            • типова пара — <ІНОЗЕМНА_ВАЛЮТА> → UAH.
        """
        for entry in api_data:
            if entry.get("currencyCodeA") == a and entry.get("currencyCodeB") == b:
                return entry                                         # ✅ Знайшли підходящий запис
        return None                                                 # 🔚 Нічого не знайшли

    async def _fetch_api_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Багатоспробне отримання даних з API валют.

        Особливості:
            • підтримуються кілька спроб (retries) з паузою між ними;
            • при успіху повертається список записів;
            • при будь-якій неуспішній спробі пишемо детальний лог.
        """
        if not self._client:
            # 🧩 Переконуємося, що HTTP-клієнт створений (ледача ініціалізація)
            await self.ensure_initialized()
            if not self._client:
                raise RuntimeError("HTTP-клієнт не ініціалізовано (initialize() не викликано).")

        for attempt in range(max(1, int(self._retries))):
            try:
                # 🌐 Відправляємо GET-запит до API валют
                response = await self._client.get(self._api_url)
                response.raise_for_status()                         # ❗ Підіймає виключення при не-2xx статусах
                api_response = response.json()
                if isinstance(api_response, list):
                    logger.info("✅ Дані з API валют успішно отримано.")
                    return api_response
                # Якщо API повернуло не список — лог і вважаємо відповідь невалідною
                logger.warning("⚠️ API валют повернуло не список, а %s", type(api_response).__name__)
                return None

            except httpx.RequestError as e:
                # ❌ Проблеми рівня мережі / таймаут і т.д.
                logger.error("❌ Спроба %s/%s: помилка API валют — %s", attempt + 1, self._retries, e)
                if attempt < self._retries - 1:
                    # ⏳ Чекаємо перед наступною спробою (простий лінійний backoff)
                    await asyncio.sleep(max(0, int(self._retry_delay)))
        # 🔚 Усі спроби виявилися невдалими
        return None

    async def _load_rates_from_file(self) -> Dict[str, Decimal]:
        """
        Безпечно читає кеш курсів з файлу. Якщо не вийшло — підтягує fallback з конфіга.

        Гарантує:
            • завжди повертає словник курсів;
            • завжди є базова валюта "UAH" з курсом 1.0.
        """
        rates: Dict[str, Decimal]
        try:
            # 📖 Пробуємо прочитати файл кешу з диску
            async with aiofiles.open(self._rate_file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                # ❗ Захист від некоректного формату файлу
                raise ValueError("Очікувався об'єкт (dict) у кеш-файлі курсів.")
            # 🔄 Нормалізуємо всі значення в Decimal і квантуємо
            rates = {k.upper(): self._quantize_rate(self._to_decimal(v)) for k, v in parsed.items()}
            logger.info("📖 Завантажено кешовані курси: %s", rates)

        except (IOError, json.JSONDecodeError, ValueError, FileNotFoundError) as e:
            # ⚠️ Будь-яка проблема з читанням файлу → fallback із конфігів
            logger.warning("⚠️ Не вдалося прочитати файл курсів (%s). Використовуються резервні значення.", e)
            fb = self._config.get("currency_api.fallback_rates", {}) or {}
            rates = {k.upper(): self._quantize_rate(self._to_decimal(v)) for k, v in fb.items()}

        # 🟡 Переконуємося, що базова валюта завжди присутня та валідна
        if "UAH" not in rates or rates.get("UAH", Decimal("0")) <= 0:
            rates["UAH"] = Decimal("1.0").quantize(self._RATE_QUANTUM, rounding=self._ROUNDING)
            logger.info("ℹ️ У кеш додається базова валюта UAH=1.0")

        # 🕒 Фіксуємо час, коли кеш було завантажено (або fallback-ом піднято)
        self._last_update_ts = time.time()
        logger.debug("📖 Кеш курсів готовий, last_update_ts=%s", self._last_update_ts)
        return rates

    async def _save_rates_to_file(self) -> None:
        """
        Пише актуальні курси у кеш-файл.

        Особливості:
            • Decimal серіалізується як рядок (str), щоб не втрачати точність;
            • JSON з відступами для зручного ручного перегляду.
        """
        payload_obj = {k: str(v) for k, v in self._rates.items()}     # 🔤 Decimal → str для JSON
        payload = json.dumps(payload_obj, indent=2, ensure_ascii=False)
        try:
            async with aiofiles.open(self._rate_file_path, "w", encoding="utf-8") as f:
                await f.write(payload)
            logger.info("💾 Кеш курсів збережено: %s", self._rates)
        except IOError as e:
            # ❌ Помилка на рівні файлової системи — лог, але не падаємо
            logger.error("❌ Помилка під час збереження курсів: %s", e)


    # ================================
    # 🧰 ДОПОМІЖНІ (безпечні числові операції)
    # ================================

    @staticmethod
    def _to_decimal(value: Union[Decimal, float, int, str]) -> Decimal:
        """
        🔢 Безпечно перетворює будь-який числовий тип у Decimal.

        Підтримувані типи:
            • Decimal — повертається як є;
            • int / float — конвертується через str для уникнення двійкових похибок;
            • str — нормалізується (trim + коми замінюються на крапки);
        
        Використовується для нормалізації будь-яких числових вхідних значень перед
        математичними операціями (особливо важливо для курсових значень).
        """
        if isinstance(value, Decimal):
            # 🔸 Уже Decimal, нічого не робимо
            return value
        if isinstance(value, (int, float)):
            # 🔸 Через str, щоб уникнути проблем із float-представленням (0.1 + 0.2 != 0.3)
            normalized = Decimal(str(value))
            logger.debug("🔢 _to_decimal CM: %r → %s", value, normalized)
            return normalized
        if isinstance(value, str):
            # 🔸 Підтримка рядків з комами ("42,50") → ("42.50")
            v = value.strip().replace(",", ".")
            normalized = Decimal(v)
            logger.debug("🔢 _to_decimal CM: %r → %s", value, normalized)
            return normalized

        # 🚫 Усі інші типи — помилка
        logger.error("❌ _to_decimal CM: непідтримуваний тип %s", type(value).__name__)
        raise ValueError(f"Непідтримуваний тип числа: {type(value).__name__}")

    def _quantize_rate(self, value: Decimal) -> Decimal:
        """
        📏 Квантує курс до 4 знаків після коми (0.0001).

        Використовується для:
            • стабільності JSON-формату при серіалізації;
            • коректних порівнянь при оновленні курсів;
            • уникнення накопичення похибок при арифметичних операціях.

        Округлення відбувається за банківським правилом (ROUND_HALF_EVEN).
        """
        quantized = value.quantize(self._RATE_QUANTUM, rounding=self._ROUNDING)
        logger.debug("📏 _quantize_rate: %s → %s", value, quantized)
        return quantized
