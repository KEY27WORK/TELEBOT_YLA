Окей, Кириле. Я зараз детально проаналізую всі твої актуальні файли (включно з base\_parser, json\_ld\_parser, formatter, availability\_handler, manager, unified\_parser, link\_handler, parser\_factory, regional\_checker) та зіставлю їх із рекомендаціями з `additional_recommendations.txt`.

Я застосую тільки ті рекомендації, з якими згоден як dev (з точки зору чистоти, логіки та архітектури), і виведу кожен оновлений файл з поясненням:

* Що змінено
* Чому саме так
* Яку проблему вирішує зміна (або як підвищує читабельність, підтримуваність чи продуктивність)

Дам знати, як усе буде готово.


## Оновлення `AvailabilityHandler` (core/product\_availability/availability\_handler.py)

**Зміни:** Додано можливість ін’єкції залежностей для гнучкості та тестування. Конструктор тепер приймає об’єкти `AvailabilityManager` і `ColorSizeFormatter` (за замовчуванням створюються стандартні). Це усуває жорстке створення об’єктів всередині класу і спрощує модульне тестування. Логіка роботи методу `handle_availability` залишилася незмінною.

```python
"""
🔹 Клас `AvailabilityHandler`:
- Отримує посилання на товар
- Витягує шлях (`product_path`)
- Використовує AvailabilityManager для перевірки наявності
- Формує публічний формат (список кольорів/розмірів) та адмінський (детально по регіонах)
"""

# 🌐 Telegram API
from telegram import Update
from telegram.ext import CallbackContext

# 📦 Логіка перевірки наявності
from core.product_availability.availability_manager import AvailabilityManager
from core.product_availability.formatter import ColorSizeFormatter
from core.parsers.base_parser import BaseParser

# 🛠️ Інфраструктура
from errors.error_handler import error_handler

# 🧰 Утиліти
from utils.url_utils import extract_product_path

# 🧱 Системні
import logging


class AvailabilityHandler:
    def __init__(self, manager: AvailabilityManager = None, formatter: ColorSizeFormatter = None):
        # Ініціалізація менеджера та форматера доступності (ін'єкція залежностей для гнучкості та тестування)
        self.manager = manager or AvailabilityManager()
        self.formatter = formatter or ColorSizeFormatter()

    @error_handler
    async def handle_availability(self, update: Update, context: CallbackContext, url: str):
        """
        📬 Основний метод: обробляє посилання на товар, перевіряє наявність і надсилає два повідомлення:
        - Публічний звіт (доступні кольори та розміри)
        - Адмінський звіт (детальна наявність по регіонах)
        """
        product_path = extract_product_path(url)
        # Отримуємо основну інформацію про товар (назва, фото) з US-сайту
        us_url = f"https://www.youngla.com{product_path}"
        parser = BaseParser(us_url)
        product_info = await parser.parse()
        title = product_info.get("title", "🔗 Товар").upper()
        image_url = product_info.get("image_url")

        logging.info(f"🛍️ Перевірка товару: {title}")
        if image_url:
            logging.info(f"🖼️ Головне зображення: {image_url}")

        # Отримуємо звіти про наявність товару
        region_checks, public_format, admin_format = await self.manager.get_availability_report(product_path)

        # Надсилаємо результати у Telegram
        if image_url:
            await update.message.reply_photo(photo=image_url, caption=title)
        else:
            await update.message.reply_text(title)
        # Публічний звіт (для користувача)
        await update.message.reply_text(
            f"{region_checks}\n\n<b>🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:</b>\n{public_format}",
            parse_mode="HTML"
        )
        # Адмінський звіт (деталізація)
        await update.message.reply_text(
            f"<b>👨‍🎓 Детально по регіонах:</b>\n{admin_format}",
            parse_mode="HTML"
        )
```

## Оновлення `AvailabilityManager` (core/product\_availability/availability\_manager.py)

**Зміни:** Усунено дублювання логіки форматування та покращено логування. Тепер замість внутрішніх методів `_merge_available_sizes` та `_get_public_format` використовується **ColorSizeFormatter** для формування текстових звітів. Це підвищує повторне використання коду та узгодженість форматування. Також додано більше контексту в логи: у попередженнях/помилках під час перевірки регіонів вказується URL товару, що допомагає швидше ідентифікувати проблемний товар. Система готова до розширення списку регіонів – для виводу прапорців та агрегування даних тепер використовується динамічний список `AvailabilityManager.REGIONS` і метод `ColorSizeFormatter.get_flag`, тож додавання нового регіону вимагатиме мінімум змін.

```python
"""
📦 availability_manager.py — Клас для мульти-регіональної перевірки та агрегації даних про наявність товарів.
"""

import logging
import asyncio
import time
from typing import Tuple, List, Dict

from core.parsers.base_parser import BaseParser
from core.parsers.json_ld_parser import JsonLdAvailabilityParser
from core.product_availability.formatter import ColorSizeFormatter

class AvailabilityManager:
    """
    🧠 Основний клас для обробки наявності товарів по регіонах:
    - Паралельно збирає дані по кольорах та розмірах з декількох регіональних сайтів (US, EU, UK).
    - Має швидку булеву перевірку товару в кожному регіоні.
    - Агрегує та форматує дані для відображення.
    """
    REGIONS = {
        "us": "https://www.youngla.com",
        "eu": "https://eu.youngla.com",
        "uk": "https://uk.youngla.com"
    }
    CACHE_TTL = 300  # секунд кешування даних

    def __init__(self):
        # Ініціалізація кешу для результатів перевірки
        self._cache: Dict[str, dict] = {}

    async def check_simple_availability(self, product_path: str) -> str:
        """
        ✅ Швидка булева перевірка наявності товару по регіонах.
        :param product_path: Шлях до товару (починаючи з '/products/...')
        :return: Рядок зі статусами наявності по регіонах (наприклад, "🇺🇸 - ✅ ...")
        """
        # Перевіряємо кеш, щоб уникнути зайвих запитів
        if product_path in self._cache:
            cached = self._cache[product_path]
            if time.time() - cached.get('time', 0) < self.CACHE_TTL:
                return cached['region_checks']

        tasks = [self._check_region_simple(region_code, product_path) for region_code in self.REGIONS]
        results = await asyncio.gather(*tasks)
        results.append("🇺🇦 - ❌")  # Україна — завжди відсутня (немає окремого сайту)
        summary = "\n".join(results)
        # Кешуємо результат швидкої перевірки окремо (без детальних даних)
        self._cache[product_path] = {
            'time': time.time(),
            'region_checks': summary
        }
        return summary

    async def _check_region_simple(self, region_code: str, product_path: str) -> str:
        """
        🔍 Перевірка доступності товару в одному регіоні (тільки True/False).
        Повертає рядок з прапорцем регіону та статусом "✅" або "❌".
        """
        flags = {"us": "🇺🇸", "eu": "🇪🇺", "uk": "🇬🇧"}
        url = f"{self.REGIONS[region_code]}{product_path}"
        try:
            parser = BaseParser(url, enable_progress=False)
            if not await parser.fetch_page():
                logging.warning(f"⚠️ Не вдалося завантажити сторінку для регіону {region_code} (URL: {url})")
                return f"{flags.get(region_code, region_code.upper())} - ❌"
            is_available = await parser.is_product_available()
            logging.info(f"{flags.get(region_code, region_code.upper())} — {'✅' if is_available else '❌'}")
            return f"{flags.get(region_code, region_code.upper())} - {'✅' if is_available else '❌'}"
        except Exception as e:
            logging.error(f"❌ Помилка перевірки регіону {region_code} (URL: {url}): {e}")
            return f"{flags.get(region_code, region_code.upper())} - ❌ (помилка)"

    async def _fetch_region_data(self, region_code: str, product_path: str) -> Tuple[str, dict]:
        """
        📥 Завантажує сторінку регіонального сайту та витягує дані про наявність кольорів/розмірів.
        Повертає кортеж (region_code, stock_data).
        """
        url = f"{self.REGIONS[region_code]}{product_path}"
        parser = BaseParser(url, enable_progress=False)
        if not await parser.fetch_page():
            logging.warning(f"⚠️ Не вдалося завантажити сторінку для регіону {region_code}")
            return region_code, {}
        # Отримуємо дані про наявність товару (колір->розміри->bool) через BaseParser
        stock_data = await parser.get_stock_data()
        return region_code, stock_data

    @staticmethod
    def _merge_global_stock(regional_data: dict) -> dict:
        """
        🔗 Об'єднує дані про наявність з різних регіонів в один словник.
        Якщо розмір доступний в будь-якому регіоні, вважаємо його доступним загалом.
        :param regional_data: {region: {color: {size: bool}}}
        """
        merged = {}
        for region, stock in regional_data.items():
            for color, sizes in stock.items():
                merged.setdefault(color, {})
                for size, available in sizes.items():
                    # Встановлюємо True, якщо хоч в одному регіоні доступно
                    merged[color][size] = merged[color].get(size, False) or available
        return merged

    async def fetch_all_regions(self, product_path: str) -> List[Tuple[str, dict]]:
        """
        📦 Паралельно отримує детальні дані про наявність з усіх регіонів (US, EU, UK).
        :return: Список кортежів [(region_code, stock_data), ...]
        """
        tasks = [self._fetch_region_data(region_code, product_path) for region_code in self.REGIONS]
        results = await asyncio.gather(*tasks)
        return results

    def _group_by_region(self, region_data: List[Tuple[str, dict]]) -> Tuple[Dict[str, Dict[str, list]], Dict[str, list]]:
        """
        🔁 Трансформує сирі дані з регіонів у дві структури:
        - per_region: {color: {region: [sizes_available]}}
        - all_sizes_map: {color: [усі розміри]} (в порядку першої появи)
        """
        grouped = {}
        all_sizes_map = {}
        for region, data in region_data:
            for color, sizes in data.items():
                for size, is_available in sizes.items():
                    # Додаємо розмір до загальної мапи (уникаємо дублювання, зберігаємо порядок)
                    if color not in all_sizes_map:
                        all_sizes_map[color] = []
                    if size not in all_sizes_map[color]:
                        all_sizes_map[color].append(size)
                    # Якщо розмір доступний, додаємо до групованої структури per_region
                    if is_available:
                        grouped.setdefault(color, {}).setdefault(region, []).append(size)
        return grouped, all_sizes_map

    async def get_availability_report(self, product_path: str) -> Tuple[str, str, str]:
        """
        📊 Виконує повну перевірку товару по регіонах та формує звіти.
        :return: Кортеж (region_checks, public_format, admin_format)
        """
        # Перевірка кешу
        if product_path in self._cache:
            cached = self._cache[product_path]
            if time.time() - cached.get('time', 0) < self.CACHE_TTL:
                return cached['region_checks'], cached['public_format'], cached['admin_format']

        # Паралельно отримуємо дані з усіх регіонів
        results = await self.fetch_all_regions(product_path)
        # Формуємо рядок швидкої перевірки по регіонах (✅/❌)
        region_lines = []
        for region, stock in results:
            # Визначаємо, чи є товар в наявності в цьому регіоні
            available = any(True for sizes in stock.values() for avail in sizes.values() if avail)
            flag = ColorSizeFormatter.get_flag(region)
            region_lines.append(f"{flag} - {'✅' if available else '❌'}")
        region_lines.append(f"{ColorSizeFormatter.get_flag('ua')} - ❌")
        region_checks = "\n".join(region_lines)
        # Групуємо дані по регіонах і об'єднуємо розміри
        per_region, all_sizes_map = self._group_by_region(results)
        merged_stock = self._merge_global_stock({region: data for region, data in results if data})
        public_format = ColorSizeFormatter.format_color_size_availability(merged_stock)
        admin_format = ColorSizeFormatter.format_admin_availability(per_region, all_sizes_map)
        # Логування детальної карти наявності по регіонах
        logging.info("📊 Детальна карта наявності по регіонах:")
        for color, regions in per_region.items():
            logging.info(f"🎨 {color}")
            for region, sizes in regions.items():
                logging.info(f"  {region.upper()}: {', '.join(sizes) if sizes else '🚫'}")
        # Збереження в кеш
        self._cache[product_path] = {
            'time': time.time(),
            'region_checks': region_checks,
            'public_format': public_format,
            'admin_format': admin_format
        }
        return region_checks, public_format, admin_format
```

## Оновлення `ColorSizeFormatter` (core/product\_availability/formatter.py)

**Зміни:** Виділено спільну функціональність форматування та забезпечено підтримку нових регіонів без змін коду. Додано статичну мапу `FLAGS` із прапорами та метод `get_flag` для отримання емодзі прапорця за кодом регіону (якщо код невідомий – будується автоматично або використовується абревіатура). Метод `format_color_size_availability` залишився аналогічним, а метод `format_admin_availability` тепер динамічно отримує список регіонів із `AvailabilityManager.REGIONS` (додаючи UA для повноти) і використовує `get_flag` для виведення прапорців. Це означає, що для додавання нового регіону достатньо прописати його URL в `AvailabilityManager.REGIONS` і за потреби додати емодзі в `FLAGS` (або він буде згенерований автоматично). Логування, що дублювалося в старій версії форматера, вилучено для скорочення коду.

```python
"""🎨 formatter.py — Форматування даних про наявність товару для Telegram."""

from typing import Dict

class ColorSizeFormatter:
    """🎨 Сервіс форматування кольорів і розмірів для відображення в Telegram."""
    # Мапа прапорців для відомих регіонів
    FLAGS = {
        "us": "🇺🇸",
        "eu": "🇪🇺",
        "uk": "🇬🇧",
        "ua": "🇺🇦"
    }

    @staticmethod
    def get_flag(region_code: str) -> str:
        """
        Повертає емодзі-прапор для заданого коду регіону (для невідомого коду повертає його верхній регістр).
        """
        if region_code in ColorSizeFormatter.FLAGS:
            return ColorSizeFormatter.FLAGS[region_code]
        if len(region_code) == 2 and region_code.isalpha():
            # Генеруємо прапор за дволітерним кодом країни (Unicode)
            return "".join(chr(0x1F1E6 + (ord(ch.upper()) - ord('A'))) for ch in region_code)
        return region_code.upper()

    @staticmethod
    def format_color_size_availability(color_data: Dict[str, Dict[str, bool]]) -> str:
        """
        📋 Форматує словник {колір: {розмір: наявність}} у зручний текстовий вигляд.
        ✅ Відображає лише розміри, які є в наявності.
        🚫 Якщо для кольору немає жодного доступного розміру — виводить 🚫.
        """
        result_lines = []
        for color, sizes in color_data.items():
            # Вибираємо тільки розміри, доступні (True)
            available_sizes = [size for size, available in sizes.items() if available]
            # Додаємо рядок для кожного кольору
            if not available_sizes:
                result_lines.append(f"• {color}: 🚫")
            else:
                result_lines.append(f"• {color}: {', '.join(available_sizes)}")
        return "\n".join(result_lines)

    @staticmethod
    def format_admin_availability(availability: Dict[str, Dict[str, list]], all_sizes_map: Dict[str, list]) -> str:
        """
        🦾 Форматує детальну карту наявності для адміністраторів.
        Показує для кожного розміру наявність (✅/🚫) у кожному регіоні (US, EU, UK, UA).
        Виводить навіть ті розміри, що відсутні всюди (позначаються 🚫 у всіх регіонах).
        :param availability: {color: {region: [sizes_available]}}
        :param all_sizes_map: {color: список усіх розмірів (у порядку появи)}
        """
        # Динамічно визначаємо актуальні регіони (UA додаємо окремо як відсутній регіон)
        from core.product_availability.availability_manager import AvailabilityManager
        regions = list(AvailabilityManager.REGIONS.keys()) + ["ua"]
        lines = []
        for color in all_sizes_map:
            lines.append(f"• {color}")
            all_sizes = all_sizes_map[color]
            for size in all_sizes:
                parts = [f"{size},"]
                for region in regions:
                    has_size = size in availability.get(color, {}).get(region, [])
                    parts.append(f"{ColorSizeFormatter.get_flag(region)} - {'✅' if has_size else '🚫'}")
                lines.append(" ".join(parts) + ";")
            lines.append("")  # порожній рядок після кожного кольору
        return "\n".join(lines)
```

## Оновлення `RegionalAvailabilityChecker` (core/product\_availability/regional\_checker.py)

**Зміни:** Метод агрегування `aggregate_availability` тепер обходить регіони динамічно на основі списку `AvailabilityManager.REGIONS` замість жорстко закодованого `["us", "eu", "uk"]`. Це гарантує, що додавання нового регіону автоматично враховується при агрегації доступних розмірів. Порядок обходу залишається стабільним (визначається порядком ключів у REGIONS). Інші методи (`check_basic`, `check_full`) залишилися без змін, оскільки вже реалізовані раніше.

```python
"""
🔹 Клас `RegionalAvailabilityChecker`:
- check_basic: короткий текстовий звіт по регіонах (✅/❌)
- check_full: повна карта наявності по регіонах (неагрегована)
- aggregate_availability: злиття даних усіх регіонів у єдину карту доступних розмірів
"""
import asyncio
from core.product_availability.availability_manager import AvailabilityManager

class RegionalAvailabilityChecker:
    @staticmethod
    async def check_basic(product_path: str) -> str:
        """
        📦 Швидка перевірка доступності товару по регіонах (US, EU, UK).
        Повертає короткий підсумок наявності у вигляді тексту з прапорцями.
        """
        manager = AvailabilityManager()
        # Використовуємо метод менеджера для швидкої перевірки
        return await manager.check_simple_availability(product_path)

    @staticmethod
    async def check_full(product_path: str) -> dict:
        """
        📊 Повний парсинг наявності через регіональні сайти.
        Повертає словник {region: {color: {size: bool}}} з даними по кожному регіону.
        """
        manager = AvailabilityManager()
        results = await manager.fetch_all_regions(product_path)
        # Перетворюємо список результатів на словник {region: stock_data}
        data_by_region = {region: stock for region, stock in results}
        return data_by_region

    @staticmethod
    def aggregate_availability(data: dict) -> dict:
        """
        🔗 Агрегує дані з усіх регіонів у єдину карту доступних розмірів.
        Наприклад, { "Black": ["M", "L"], "White": ["S"] } для розмірів, що є в наявності.
        :param data: Словник по регіонах: {region: {color: {size: bool}}}
        :return: Словник {color: [розміри, доступні хоча б в одному регіоні]}
        """
        aggregated_data: dict = {}
        # Проходимо регіони у порядку, заданому в AvailabilityManager.REGIONS (для стабільності)
        for region in AvailabilityManager.REGIONS:
            if region in data:
                for color, sizes in data[region].items():
                    for size, available in sizes.items():
                        if available:
                            aggregated_data.setdefault(color, [])
                            if size not in aggregated_data[color]:
                                aggregated_data[color].append(size)
        return aggregated_data
```

## Оновлення методу `BaseParser.parse` (core/parsers/base\_parser.py)

**Зміни:** Метод `parse` оптимізовано за допомогою паралельного виконання незалежних підзадач через `asyncio.gather`. Після успішного завантаження сторінки всі основні дані (назва, опис, секції, зображення, список кольорів і розмірів, галерея зображень, ціна) витягуються одночасно, що може прискорити загальний парсинг, особливо на сторінках з великим обсягом даних. Логіка об’єднання короткого опису з детальними секціями залишається такою ж, але тепер виконуються вже після отримання всіх даних. Результат формується ідентично до попередньої версії (ключі словника не змінились). Ця зміна робить код більш ефективним і демонструє кращі практики асинхронності, не впливаючи на зовнішню функціональність.

```python
    async def parse(self) -> Dict[str, Any]:
        """
        📥 Парсить сторінку та збирає всі доступні дані про товар.
        Повертає словник із ключовою інформацією.
        """
        if not await self.fetch_page():
            return {}
        # Паралельно отримуємо основні поля товару
        title_task = self.extract_title()
        description_task = self.extract_description()
        sections_task = self.extract_detailed_sections()
        image_task = self.extract_image()
        colors_task = self.format_colors_with_stock()
        images_task = self.extract_all_images()
        price_task = self.extract_price()
        title, description, detailed_sections, image_url, colors_text, images, price = await asyncio.gather(
            title_task, description_task, sections_task, image_task, colors_task, images_task, price_task
        )
        # Якщо опис надто короткий, доповнюємо першим розділом з detail-розділів
        if not description or len(description.strip()) < 20:
            if detailed_sections:
                first_key = next(iter(detailed_sections))
                description = detailed_sections[first_key]
        weight = await self.determine_weight(title, description, image_url)
        currency = self.currency

        return {
            "title": title,
            "price": price,
            "currency": currency,
            "description": description,
            "main_image": image_url,
            "colors_sizes": colors_text,
            "images": images,
            "weight": weight,
            "sections": detailed_sections,
            "image_url": image_url,
        }
```

**Примітка:** Усі внесені правки узгоджуються з рекомендаціями з файлу `additional_recommendations.txt`. Код став більш модульним і гнучким – форматування винесено в окремий клас, покращено повторне використання, прибрано зайвий дубльований код, а асинхронні виклики оптимізовано. Логування тепер надає більше контексту для зручності відладки. Важливо, що ці зміни не змінюють зовнішню поведінку системи, всі існуючі тести повинні проходити успішно. Система готова до розширення – додавання нових регіонів чи методів перевірки потребуватиме мінімальних змін у зазначених структурах.
