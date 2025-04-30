""" 📦 availability_checker.py — Перевірка наявності товару в регіонах YoungLA.

Функції:
- check_availability_across_regions — асинхронно перевіряє наявність товару у US, EU, UK.
"""

import asyncio
import logging
from typing import Tuple

from core.parsing.base_parser import BaseParser


async def _check_region_availability(domain: str, product_path: str) -> Tuple[str, str]:
    """
    🔍 Перевіряє наявність товару в одному регіоні.

    :param domain: Домен регіону (https://www.youngla.com)
    :param product_path: Шлях до товару (/products/назва)
    :return: (🇺🇸/🇪🇺/🇬🇧, "✅"/"❌")
    """
    url = domain + product_path
    parser = BaseParser(url)

    if not await parser.fetch_page():
        return ("❌", domain)

    is_available = await parser.is_product_available()
    region_flag = _region_to_flag(parser.currency)

    return ("✅", region_flag) if is_available else ("❌", region_flag)


def _region_to_flag(currency: str) -> str:
    return {
        "USD": "🇺🇸",
        "EUR": "🇪🇺",
        "GBP": "🇬🇧",
    }.get(currency, "❓")


async def check_availability_across_regions(product_path: str) -> str:
    """
    🔄 Перевіряє наявність товару у всіх трьох регіонах.

    :param product_path: Шлях до товару (/products/назва)
    :return: Наприклад: 🇺🇸 - ✅\n🇪🇺 - ❌\n🇬🇧 - ✅
    """
    domains = [
        "https://www.youngla.com",
        "https://eu.youngla.com",
        "https://uk.youngla.com",
    ]

    tasks = [_check_region_availability(domain, product_path) for domain in domains]
    results = await asyncio.gather(*tasks)

    availability_lines = [f"{flag} - {status}" for status, flag in results]
    return "\n".join(availability_lines)

