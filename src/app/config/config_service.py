# ⚙️ config_service.py
"""
⚙️ config_service.py — Сервіс для доступу до статичної конфігурації.

🔹 Клас `ConfigService`:
- Завантажує конфігурацію з .env, config.json та config.yaml.
- Надає єдиний метод .get() для доступу до будь-якого параметра.
- Працює як Singleton.
"""

# 🌐 Зовнішні бібліотеки
import yaml                                  # 📦 YAML-парсинг
from dotenv import load_dotenv              # 🔐 Завантаження змінних із .env

# 🔠 Системні імпорти
import os                                   # 📁 Доступ до змінних середовища
import json                                 # 📄 Робота з JSON-файлами
import logging                              # 🧾 Логування
from pathlib import Path                    # 📁 Побудова шляху до файлів
from typing import Any, Dict                # 🧩 Типізація


# ============================
# ⚙️ СЕРВІС ДОСТУПУ ДО КОНФІГІВ
# ============================
class ConfigService:
    """
    ⚙️ Надає доступ до всіх статичних конфігураційних параметрів проєкту.
    Працює як Singleton — конфігурація зчитується лише один раз.
    """

    _instance = None                          # 🧩 Singleton-екземпляр
    _config: Dict[str, Any] = {}              # 📦 Обʼєднана конфігурація зі всіх джерел

    def __new__(cls):
        # ✅ Патерн Singleton: створюємо лише один екземпляр
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all_configs()  # 🔄 Завантаження конфігурації під час першого виклику
            logging.debug("🔄 Singleton ConfigService створено і конфігурація завантажена")
        else:
            logging.debug("📦 Використовується існуючий екземпляр ConfigService")
        return cls._instance

    def _load_all_configs(self):
        """
        📥 Завантажує всі джерела конфігурації в один словник.
        Пріоритет: .env → config.json → config.yaml
        """

        # --- 1. .env змінні ---
        logging.debug("🔐 Завантаження змінних з .env")
        load_dotenv()  # 🔐 Ініціалізує змінні середовища з файлу .env
        env_vars = {
            "telegram.bot_token": os.getenv("TELEGRAM_TOKEN"),
            "openai.api_key": os.getenv("OPENAI_API_KEY")
        }
        # 🔁 Перетворюємо крапкові ключі в словник та обʼєднуємо з config
        self._deep_update(self._config, self._unflatten_dict(env_vars))

        # --- 2. JSON-файл ---
        try:
            logging.debug("📄 Завантаження config.json")
            json_path = Path(__file__).parent / "config.json"
            with open(json_path, "r", encoding="utf-8") as f:
                self._deep_update(self._config, json.load(f))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"⚠️ Не вдалося завантажити config.json: {e}")

        # --- 3. YAML-файл ---
        try:
            logging.debug("📘 Завантаження config.yaml")
            yaml_path = Path(__file__).parent / "config.yaml"
            with open(yaml_path, "r", encoding="utf-8") as f:
                self._deep_update(self._config, yaml.safe_load(f))
        except (FileNotFoundError, yaml.YAMLError) as e:
            logging.warning(f"⚠️ Не вдалося завантажити config.yaml: {e}")

        logging.info("✅ Конфігурацію успішно завантажено.")
        logging.debug(f"🔍 Обʼєднаний словник конфігурації: {self._config}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        🔑 Отримує значення конфігурації за ключем (наприклад: 'telegram.bot_token').

        Args:
            key (str): Ключ у форматі з крапкою.
            default (Any): Значення за замовчуванням, якщо ключ не знайдено.

        Returns:
            Any: Значення параметра або default.
        """
        keys = key.split('.')                     # ⛓️ Розбиваємо ключ за крапкою
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]                 # 🔎 Переходимо глибше в структуру
            else:
                logging.debug(f"❓ Ключ '{key}' не знайдено, повертаємо значення за замовчуванням")
                return default                   # ❌ Якщо ключ не знайдено — повертаємо дефолт
        logging.debug(f"📥 Ключ '{key}' знайдено, значення: {value}")
        return value                              # ✅ Повертаємо значення

    # ===============================
    # 🔧 ДОПОМІЖНІ МЕТОДИ ЗЛИТТЯ КОНФІГІВ
    # ===============================

    def _unflatten_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔁 Перетворює ключі з крапками в ієрархічний словник.
        'telegram.token' → {'telegram': {'token': ...}}
        """
        logging.debug("🔃 Перетворення ключів з крапками в ієрархічний словник")
        result = {}
        for key, value in d.items():
            parts = key.split('.')                   # 🧩 Розбиваємо ключ на частини
            d_ref = result
            for part in parts[:-1]:                  # 🔁 Ітеруємось по вкладеності
                if part not in d_ref:
                    d_ref[part] = {}
                d_ref = d_ref[part]
            d_ref[parts[-1]] = value                 # 🧷 Вставляємо значення у найглибший рівень
        logging.debug(f"📦 Результат перетворення: {result}")
        return result

    def _deep_update(self, source: Dict, overrides: Dict):
        """
        🔁 Рекурсивно обʼєднує два словника (оновлення значень).
        Якщо значення — словник, обʼєднує його глибоко.
        """
        for key, value in overrides.items():
            if (
                isinstance(value, dict) and
                key in source and
                isinstance(source[key], dict)
            ):
                self._deep_update(source[key], value)  # 🔁 Глибоке обʼєднання
            else:
                source[key] = value                    # 🧩 Перезапис простого значення
        logging.debug(f"🔁 Поточний словник після оновлення: {source}")