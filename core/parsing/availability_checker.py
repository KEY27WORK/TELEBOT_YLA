""" 🛒 availability_checker.py — Перевірка наявності товару в регіонах YoungLA.

🔹 Функції:
- check_availability_across_regions — перевіряє доступність товару у US, EU, UK.

Використовує:
- UniversalProductParser для перевірки наявності
"""

# 📦 Імпорти
from core.parsing.products.universal_product_parser import UniversalProductParser


async def check_availability_across_regions(product_path: str) -> str:
    """
    🔍 Перевіряє наявність товару у всіх регіонах.

    :param product_path: Частина URL товару без домену (наприклад, /products/назва)
    :return: Рядок із прапорцями регіонів та статусом
    """
    regions = {
        "🇺🇸": "https://www.youngla.com",
        "🇪🇺": "https://eu.youngla.com",
        "🇬🇧": "https://uk.youngla.com",
    }
    availability = {}

    for flag, domain in regions.items():
        url = domain + product_path
        parser = UniversalProductParser(url)

        # 🛠 ОБОВ'ЯЗКОВО завантажуємо сторінку перед перевіркою!
        if not await parser.fetch_page():
            availability[flag] = "❌"
            continue

        is_available = await parser.is_product_available()
        availability[flag] = "✅" if is_available else "❌"

       # 🛒 Додаємо завжди 🇺🇦 (бо немає локального складу)
    availability["🇺🇦"] = "❌"

    # 🔥 Завжди виводимо всі прапори
    result = "\n".join(f"{flag} - {status}" for flag, status in availability.items())
    return result


