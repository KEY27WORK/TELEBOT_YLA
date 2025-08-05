# ⚖️ app/infrastructure/data_storage/weight_data_service.py
"""
⚖️ weight_data_service.py — Асинхронний сервіс для роботи з локальною базою ваг.
"""

# 🔠 Системні імпорти
import json                                                    # 📦 Робота з JSON-структурами
import logging                                                 # 🧾 Логування подій
from typing import Dict                                        # 🧰 Типізація словника
import aiofiles                                                # 📂 Асинхронна робота з файлами
import asyncio                                                 # 🔄 Асинхронні блокування та таски

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService            # ⚙️ Сервіс конфігурації (шлях до файлу)
from app.shared.utils.logger import LOG_NAME                   # 📝 Загальна назва для логів

logger = logging.getLogger(LOG_NAME)                           # 🧾 Ініціалізація логера


# ================================
# ⚖️ СЕРВІС ЗБЕРІГАННЯ ВАГИ
# ================================
class WeightDataService:
    """
    ⚖️ Сервіс для асинхронного читання, запису та оновлення ваги товарів
    у локальному JSON-файлі.
    """

    def __init__(self, config_service: ConfigService):
        """
        🔌 Ініціалізація сервісу зі шляхом до файлу та локом для потокобезпечності.
        """
        self.weight_file_path = config_service.get("files.weights", "weights.json")			# 📍 Отримуємо шлях до файлу ваг
        self._lock = asyncio.Lock()													# 🔒 Лок для захисту від одночасного доступу
        logger.info(f"⚖️ WeightDataService ініціалізовано (файл: {self.weight_file_path})")

    async def load(self) -> Dict[str, float]:
        """
        📥 Завантажує ваги з локального JSON-файлу.

        Returns:
            Dict[str, float]: Словник товарів з вагами
        """
        async with self._lock:
            try:
                async with aiofiles.open(self.weight_file_path, "r", encoding="utf-8") as f:
                    content = await f.read()                                       # 📄 Читання JSON-рядка
                    return json.loads(content)                                    # 🔄 Парсинг у словник
            except (FileNotFoundError, json.JSONDecodeError):                     # 🧯 Якщо файл не знайдено або JSON пошкоджено
                return {}                                                         # ↩️ Повертаємо порожній словник

    async def save(self, data: Dict[str, float]):
        """
        💾 Зберігає словник ваг у локальний файл у форматі JSON.

        Args:
            data (Dict[str, float]): Дані для збереження
        """
        async with self._lock:
            try:
                async with aiofiles.open(self.weight_file_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, indent=4, ensure_ascii=False))   # ✅ Форматований запис у файл
                logger.info("✅ Ваги товарів збережено.")                           # 🧾 Успішне збереження
            except Exception as e:
                logger.error(f"❌ Помилка збереження ваги: {e}")                    # 🧯 Обробка критичних помилок

    async def update(self, product_name: str, weight: float):
        """
        ♻️ Оновлює або додає нову вагу для товару.

        Args:
            product_name (str): Назва товару
            weight (float): Вага в кг
        """
        data = await self.load()                                                   # 📥 Завантажуємо поточні дані
        data[product_name.lower()] = weight                                        # 🆕 Додаємо або оновлюємо ключ
        await self.save(data)                                                      # 💾 Зберігаємо назад у файл
        logger.info(f"♻️ Вага оновлена: {product_name} = {weight} кг")             # 🧾 Лог зміни
