""" 🛒 availability_checker.py — Перевірка наявності товару в регіонах YoungLA.

🔹 Функції:
- check_availability_across_regions — асинхронно перевіряє доступність товару у US, EU, UK.

Використовує:
- UniversalProductParser для перевірки наявності
"""

# 📦 Імпорти
import asyncio
from core.parsing.products.universal_product_parser import UniversalProductParser


async def _check_region_availability(domain: str, product_path: str) -> tuple[str, str]:
    """
    🔍 Асинхронна перевірка доступності товару в одному регіоні.

    :param domain: Домен регіону (наприклад, https://www.youngla.com)
    :param product_path: Шлях продукту (наприклад, /products/назва)
    :return: Кортеж (прапор регіону, статус '✅' або '❌')
    """
    url = domain + product_path
    parser = UniversalProductParser(url)

    if not await parser.fetch_page():
        return ("❌", domain)  # Якщо сторінку не вдалося завантажити

    is_available = await parser.is_product_available()
    return ("✅" if is_available else "❌", domain)


async def check_availability_across_regions(product_path: str) -> str:
    """
    🔍 Перевіряє наявність товару у всіх регіонах паралельно.

    :param product_path: Частина URL товару без домену (наприклад, /products/назва)
    :return: Рядок із прапорцями регіонів та статусом
    """
    regions = {
        "🇺🇸": "https://www.youngla.com",
        "🇪🇺": "https://eu.youngla.com",
        "🇬🇧": "https://uk.youngla.com",
    }

    # 🔥 Паралельний запуск всіх регіонів
    tasks = [ _check_region_availability(domain, product_path) for domain in regions.values() ]
    results = await asyncio.gather(*tasks)

    # 📦 Формуємо підсумкову мапу
    availability = dict(zip(regions.keys(), [status for status, _ in results]))

    # Додаємо Україну 🇺🇦 (поки що завжди ❌)
    availability["🇺🇦"] = "❌"

    # 📋 Формуємо фінальний текст
    result_text = "\n".join(f"{flag} - {status}" for flag, status in availability.items())
    return result_text


