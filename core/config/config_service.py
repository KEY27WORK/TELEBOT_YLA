"""
⚙️ config_service.py — Сервіс конфігурації для Telegram-бота YoungLA Ukraine.

🔹 Клас `ConfigService`:
- Завантажує API-ключі з .env
- Отримує курс валют через API НБУ
- Керує локальною базою ваг товарів (JSON)
- Працює як Singleton

Використовує:
- requests для запитів до API
- dotenv для змінних середовища
- logging для логів
- json / os / pathlib
"""

import logging
import json
import os
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class ConfigService:
    """📦 Клас для управління конфігурацією, API-ключами, курсами валют та локальною базою ваг."""

    _instance = None
    _config = None
    _exchange_cache = {}

    WEIGHT_FILE = "weights.json"
    PRODUCT_TYPE_FILE = "product_types.json"
    FALLBACK_RATES = {"USD": 42.0, "GBP": 55.0, "EUR": 46.0}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_env()
        return cls._instance

    def __init__(self):
        self.weight_file = self.WEIGHT_FILE

    def _load_env(self):
        """🔐 Завантаження змінних із .env"""
        load_dotenv()
        self._telegram_token = os.getenv("TELEGRAM_TOKEN")
        self._openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self._telegram_token:
            logging.critical("❌ TELEGRAM_TOKEN не знайдено у .env")
        if not self._openai_api_key:
            logging.critical("❌ OPENAI_API_KEY не знайдено у .env")

    @property
    def telegram_token(self) -> str:
        """🔑 API-ключ Telegram"""
        return self._telegram_token

    @property
    def openai_api_key(self) -> str:
        """🔑 API-ключ OpenAI"""
        return self._openai_api_key

    # === Конфігураційний JSON ===

    @classmethod
    def load_config(cls):
        if cls._config is None:
            config_path = Path(__file__).parent / "config.json"
            with open(config_path, "r", encoding="utf-8") as file:
                cls._config = json.load(file)
        return cls._config

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        return cls.load_config().get(key, default)

    # === Курс валют ===

    def fetch_exchange_rate(self, currency: str) -> float:
        """
        💱 Отримує актуальний курс валют через API НБУ.

        🔁 Алгоритм дій:
        1. Якщо курс уже є в кеші — повертає з кешу
        2. Інакше — робить HTTP-запит до API НБУ
        3. Якщо відповідь валідна — кешує та повертає курс
        4. Якщо щось пішло не так (нема курсу, помилка мережі, порожня відповідь) — повертає fallback

        🔐 Надійна поведінка навіть у разі відсутності інтернету або якщо НБУ не відповідає.

        :param currency: Код валюти (наприклад, 'USD', 'EUR', 'GBP')
        :return: Поточний курс до гривні (float)
        """

        # 🔎 Перевірка, чи вже є кешований курс для цієї валюти
        if currency in self._exchange_cache:
            return self._exchange_cache[currency]

        # 🌐 Формуємо URL для запиту до НБУ
        url = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode={currency}&json"
        try:
            # 🚀 Відправляємо GET-запит із таймаутом 5 секунд
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Піднімає виняток, якщо статус не 200

            # 🧾 Розпарсюємо відповідь
            data = response.json()

            # ⚠️ Перевірка на валідність даних (порожній список або відсутність поля "rate")
            if not data or "rate" not in data[0]:
                raise ValueError(f"Валюта {currency} не знайдена в API НБУ")

            # ✅ Отримуємо курс і кешуємо його
            rate = float(data[0]["rate"])
            logging.info(f"💰 Курс {currency}: {rate} грн")

            # ⛑ Мінімальний курс безпеки — не нижче 42.3
            self._exchange_cache[currency] = max(rate, 42.3)
            return self._exchange_cache[currency]

        except (requests.RequestException, ValueError, IndexError) as e:
            # 🧯 У разі помилки — лог і fallback
            logging.error(f"❌ Помилка отримання курсу {currency}: {e}")
            return self.FALLBACK_RATES.get(currency, 42.0)


    # === Робота з вагою товарів ===

    def load_weight_data(self) -> dict[str, float]:
        """
        📥 Завантажує вагу товарів із локального JSON-файлу.
    
        🔁 Алгоритм:
        - Якщо файл не існує — повертає порожній словник
        - Якщо файл є — читає його та повертає словник типу {назва: вага}
    
        :return: Словник ваг типу {"hoodie": 1.2, "tee": 0.3}
        """
        try:
            if not os.path.exists(self.weight_file):
                logging.warning("⚠️ Файл ваги не знайдено. Створюється новий.")
                return {}
    
            with open(self.weight_file, "r", encoding="utf-8") as file:
                return json.load(file)
    
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"⚠️ Помилка при завантаженні ваги: {e}")
            return {}

    def save_weight_data(self, data: dict[str, float]):
        """
        💾 Зберігає словник ваг у JSON-файл.

        🔒 Забезпечує збереження змін у weights.json.
        Форматує JSON красиво (indent=4), без втрати кирилиці (ensure_ascii=False).

        :param data: Словник типу {"hoodie": 1.2, "tee": 0.3}
        """
        try:
            with open(self.weight_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            logging.info("✅ Вага товарів збережена.")
        except Exception as e:
            logging.error(f"❌ Помилка збереження ваги: {e}")

    def register_weight(self, product_name: str, weight: float):
        """
        📌 Реєструє нову вагу тільки якщо вона ще не внесена.

        🔒 Використовується для первинного збереження ваги:
        - Якщо товар уже є — нічого не змінює
        - Якщо товар новий — додає його в JSON

        :param product_name: Назва типу товару або унікальний ідентифікатор
        :param weight: Вага в кілограмах (float)
        """
        data = self.load_weight_data()
        if product_name not in data:
            data[product_name] = weight
            self.save_weight_data(data)
            logging.info(f"➕ Додано нову вагу: {product_name} = {weight} кг")

    def update_weight_dict(self, product_name: str, weight: float):
        """
        ♻️ Оновлює або додає вагу товару у weights.json.

        🔁 Якщо вага вже є — перезаписує її.
        Використовується, коли GPT перерахував нову вагу точніше.

        :param product_name: Назва типу товару або унікальний ключ
        :param weight: Нова вага (float)
        """
        data = self.load_weight_data()
        data[product_name] = weight
        self.save_weight_data(data)
        logging.info(f"♻️ Вага оновлена: {product_name} = {weight} кг")

    # === Типи товарів ===

    def load_product_types(self) -> dict[str, float]:
        """📥 Завантажує відомі типи товарів із JSON."""
        try:
            if not os.path.exists(self.PRODUCT_TYPE_FILE):
                logging.warning("⚠️ Файл типів товарів не знайдено. Створюється новий.")
                return {}
            with open(self.PRODUCT_TYPE_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            logging.warning(f"⚠️ Помилка при завантаженні типів товарів: {e}")
            return {}

    def save_product_types(self, types: dict[str, float]):
        """💾 Зберігає типи товарів із вагою."""
        try:
            with open(self.PRODUCT_TYPE_FILE, "w", encoding="utf-8") as file:
                json.dump(types, file, indent=4, ensure_ascii=False)
            logging.info("✅ Типи товарів збережено.")
        except Exception as e:
            logging.error(f"❌ Помилка збереження типів товарів: {e}")

    def update_product_type(self, product_type: str, weight: float):
        """🧠 Оновлює або додає новий тип товару та його вагу."""
        types = self.load_product_types()
        if product_type not in types or types[product_type] != weight:
            types[product_type] = weight
            self.save_product_types(types)
            logging.info(f"🆕 Додано/оновлено тип товару: {product_type} = {weight} кг")