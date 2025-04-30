""" ✅ availability_checker.py — Перевірка наявності товару в різних регіонах (US, EU, UK)

🔹 Функція `check_availability_across_regions()`:
- Паралельно перевіряє наявність товару в регіонах
- Повертає зведене повідомлення для Telegram

Використовує:
- BaseParser для парсингу
- asyncio для паралельного виконання
- logging для діагностики
"""

# 📦 Стандартні
import asyncio
import logging
from urllib.parse import urlparse

# 🧠 Парсер
from core.parsing.base_parser import BaseParser

# --- 🔁 Основна функція ---

async def check_availability_across_regions(product_path: str) -> str:
    """
    🔍 Перевіряє наявність товару на сайтах US, EU та UK паралельно.

    :param product_path: Шлях до продукту (без домену)
    :return: Форматоване повідомлення з наявністю по регіонах
    """
    urls = {
        "🇺🇸": f"https://www.youngla.com{product_path}",
        "🇪🇺": f"https://eu.youngla.com{product_path}",
        "🇬🇧": f"https://uk.youngla.com{product_path}"
    }

    logging.info(f"🌍 Перевірка наявності в регіонах: {urls}")

    tasks = [
        _check_region_availability(region, url)
        for region, url in urls.items()
    ]
    results = await asyncio.gather(*tasks)

    summary = "\n".join(results)
    summary += "\n🇺🇦 - ❌"
    
    return summary


# --- 🧪 Допоміжна функція для окремого регіону ---

async def _check_region_availability(region_flag: str, url: str) -> str:
    """
    📦 Перевіряє наявність товару в одному регіоні за URL.

    :param region_flag: Емодзі регіону (🇺🇸/🇪🇺/🇬🇧)
    :param url: Повний URL до товару
    :return: Статус в форматі «🇺🇸 - ✅ / ❌»
    """
    try:
        parser = BaseParser(url, enable_progress=False)
        await parser.fetch_page()
        available = await parser.is_product_available()
        return f"{region_flag} - {'✅' if available else '❌'}"
    except Exception as e:
        logging.error(f"❌ Помилка перевірки для {url}: {e}")
        return f"{region_flag} - ❌ (помилка)"
