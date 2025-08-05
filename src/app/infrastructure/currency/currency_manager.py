# 💵 app/infrastructure/currency/currency_manager.py
"""
💵 currency_manager.py — Асинхронний менеджер валют з кешуванням.

🔹 Клас `CurrencyManager`:
    • Отримує курси валют із API
    • Кешує результати у файл
    • Додає націнку до курсів (margin)
    • Має retry-логіку при помилках
"""

# 🌐 Зовнішні бібліотеки
import httpx											# 🌐 HTTP-клієнт для запитів до API
import aiofiles										# 📁 Асинхронна робота з файлами

# 🔠 Системні імпорти
import asyncio										# 🔄 Асинхронність
import json											# 📦 Робота з JSON-даними
import logging										# 🧾 Логування
from typing import Dict, Optional, List, Any						# 🧰 Типи

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService			# ⚙️ Сервіс конфігурації
from app.shared.utils.logger import LOG_NAME					# 🧾 Назва логгера

logger = logging.getLogger(LOG_NAME)

# ================================
# 💱 МЕНЕДЖЕР ВАЛЮТ
# ================================
class CurrencyManager:
    """ 💱 Керує отриманням, кешуванням та оновленням курсів валют асинхронно. """

    UAH_CODE = 980										# 🇺🇦 Код валюти гривні

    def __init__(self, config_service: ConfigService):
        self.config = config_service								# ⚙️ Збереження DI-конфігурації
        self.api_url = self.config.get("currency_api.url")			# 🔗 URL для запиту курсів
        self.rate_file_path = self.config.get("files.currency_rates")		# 🧾 Шлях до JSON-файлу кешу
        self.currency_codes = self.config.get("currency_api.codes", {})	# 🌍 Валюти, які нас цікавлять
        self.margin = self.config.get("currency_api.margin", 0.5)		# 💰 Націнка
        self.timeout = self.config.get("currency_api.timeout_sec", 5)	# ⏱️ Таймаут запиту
        self.retries = self.config.get("currency_api.retry_attempts", 2)	# 🔁 К-сть спроб
        self.retry_delay = self.config.get("currency_api.retry_delay_sec", 2)	# ⏳ Затримка між спробами

        self.rates: Dict[str, float] = {}							# 💵 Актуальні курси
        self._api_data_cache: Optional[List[Dict[str, Any]]] = None				# 🧠 Кеш API-відповіді
        self._lock = asyncio.Lock()								# 🔐 Асинхронний lock для запису

    async def initialize(self):
        """ 🏁 Завантажує курси валют з кеш-файлу при старті. """
        self.rates = await self._load_rates_from_file()			# 📥 Кешування в памʼять
        logger.info("🔧 CurrencyManager ініціалізовано")

    async def _load_rates_from_file(self) -> Dict[str, float]:
        """ 📖 Завантажує курси валют з локального JSON-файлу. """
        try:
            async with aiofiles.open(self.rate_file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                logger.info(f"📖 Завантажено кешовані курси: {data}")
                return data
        except (IOError, json.JSONDecodeError, FileNotFoundError):
            logger.warning("⚠️ Неможливо прочитати файл з курсами. Використовуються резервні.")
            fallback = self.config.get("currency_api.fallback_rates", {})
            return {**fallback, "UAH": 1.0}						# 🔁 Повертаємо fallback + гривню

    async def _save_rates_to_file(self):
        """ 💾 Зберігає курси у кеш-файл. """
        async with self._lock:
            try:
                async with aiofiles.open(self.rate_file_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(self.rates, indent=2))
                    logger.info(f"💾 Кеш курсів оновлено: {self.rates}")
            except IOError as e:
                logger.error(f"❌ Помилка при збереженні курсів: {e}")

    async def _fetch_api_data(self) -> List[Dict[str, Any]]:
        """ 🌐 Отримує нові курси з API Monobank. Має retry та кеш. """
        if self._api_data_cache is not None:
            return self._api_data_cache             # 🧠 Віддаємо з кешу

        async with httpx.AsyncClient() as client:
            for attempt in range(self.retries):
                try:
                    response = await client.get(self.api_url, timeout=self.timeout)
                    response.raise_for_status()
                    api_response = response.json()
                    # ✅ (ВИПРАВЛЕНО) Додаємо перевірку, що відповідь є списком
                    if isinstance(api_response, list):
                        self._api_data_cache = api_response
                        logger.info("✅ Дані з API валют успішно отримані")
                        return self._api_data_cache
                    else:
                        logger.warning(f"⚠️ API валют повернуло несподіваний тип: {type(api_response)}")
                except httpx.RequestError as e:
                    logger.error(f"❌ Спроба {attempt+1}: Помилка API валют — {e}")
                    await asyncio.sleep(self.retry_delay)

        self._api_data_cache = []               # 🧯 У разі фейлу — порожній список
        return self._api_data_cache

    async def update_all_rates(self):
        """
        🔄 Оновлює всі курси: тільки якщо з API надійшли нові (вищі) значення.
        """
        api_data = await self._fetch_api_data()
        was_updated = False

        for currency, code in self.currency_codes.items():
            try:
                for entry in api_data:
                    if entry.get("currencyCodeA") == code and entry.get("currencyCodeB") == self.UAH_CODE:
                        raw_rate = entry.get("rateSell") or entry.get("rateCross") or entry.get("rateBuy")
                        if not raw_rate:
                            continue

                        new_rate = round(float(raw_rate) + self.margin, 2)		# 💰 Додаємо margin
                        old_rate = self.rates.get(currency, 0)

                        if new_rate > old_rate:
                            logger.info(f"🔺 Курс {currency} оновлено: {old_rate} → {new_rate}")
                            self.rates[currency] = new_rate
                            was_updated = True
                        break
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Помилка оновлення курсу {currency}: {e}")

        if was_updated:
            await self._save_rates_to_file()						# 💾 Зберігаємо тільки при зміні

    def get_all_rates(self) -> Dict[str, float]:
        """ 📤 Повертає усі актуальні курси у словнику. """
        return self.rates
    
    async def set_rate_manually(self, currency: str, rate: float):
        """
        ✅ (НОВЕ) Встановлює курс для валюти вручну та зберігає у файл.
        """
        self.rates[currency.upper()] = rate
        await self._save_rates_to_file()