# 🧠 app/infrastructure/parsers/base_parser.py
"""
🧠 base_parser.py — Оркестратор парсингу сторінки товару.

🔹 Клас `BaseParser`:
- Реалізує повний цикл обробки сторінки одного товару.
- Використовує впроваджені залежності (WebDriver, Translator, Config).
- Делегує витяг даних з HTML класу `HtmlDataExtractor`.
- Містить логіку fallback для stock та маппінг розмірів.
- Агрегує дані та повертає об'єкт `ProductInfo`.
"""

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup           # 🧽 Парсинг HTML
from rich.progress import (             # ⏳ Вивід прогресу в термінал
    Progress, SpinnerColumn,
    TextColumn, TimeElapsedColumn
    )            

# 🔠 Системні імпорти
import logging                      # 🧾 Логування
import re                           # 🔤 Регулярні вирази
from typing import (                # 🧰 Типізація
    Any, Dict, Optional                         
    )
# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService                             # ⚙️ Конфігурація (включаючи ваги)
from app.domain.products.entities import ProductInfo                            # 📦 Сутність товару
from app.domain.products.interfaces import IProductDataProvider                 # 🧱 Контракт для парсерів
from app.domain.products.services.weight_resolver import WeightResolver         # ⚖️ Визначення ваги
from app.infrastructure.ai.translator import TranslatorService                  # 🤖 GPT-сервіс для fallback опису
from app.infrastructure.web.webdriver_service import WebDriverService           # 🌍 Завантаження HTML-сторінки
from app.shared.utils.url_parser_service import UrlParserService                # 🔗 Сервіс для роботи з URL
from .html_data_extractor import HtmlDataExtractor                              # 🕷️ Витяг структурованих даних


# ================================
# 🏛️ ГОЛОВНИЙ КЛАС ПАРСЕРА
# ================================
class BaseParser(IProductDataProvider):
    """
    📦 Відповідає за повний цикл обробки сторінки товару YoungLA:
    завантаження → витяг даних → обробка → формування ProductInfo.
    """

    # ================================
    # ⚙️ ІНІЦІАЛІЗАЦІЯ
    # ================================
    def __init__(
        self,
        url: str,
        webdriver_service: WebDriverService,
        translator_service: TranslatorService,
        config_service: ConfigService,
        weight_resolver: WeightResolver,
        url_parser_service: UrlParserService,
        enable_progress: bool = True,
    ):
        self.url = url													            # 🔗 URL сторінки товару
        self.webdriver_service = webdriver_service									# 🌍 Сервіс завантаження HTML
        self.translator_service = translator_service								# 🤖 Перекладач для fallback описів
        self.config_service = config_service										# ⚙️ Конфігурація (наприклад, для user-agent)
        self.weight_resolver = weight_resolver									    # ⚖️ Сервіс для визначення ваги товару
        self.url_parser_service = url_parser_service
        self.enable_progress = enable_progress									    # ⏳ Включити прогрес-бар в терміналі

        self._currency = self.url_parser_service.get_currency(url)					# 💱 Отримання валюти за URL (us/eu/uk)

        self.page_source: Optional[str] = None									    # 📄 HTML-код сторінки як сирий текст
        self._page_soup: Optional[BeautifulSoup] = None							    # 🧽 Парсене дерево DOM для подальшого аналізу

    # ================================
    # 🔄 ПУБЛІЧНИЙ ІНТЕРФЕЙС
    # ================================
    async def get_product_info(self) -> ProductInfo:
        """
        🔄 Основний метод: запускає повний пайплайн і повертає ProductInfo.
        """
        try:
            await self._fetch_and_prepare_soup()								        # 🌍 Завантаження сторінки та створення soup-дерева
            if not self._page_soup:
                raise ConnectionError(
                    "Не вдалося завантажити або розпарсити HTML."
                    )

            extractor = HtmlDataExtractor(self._page_soup)						        # 🕷️ Створення екстрактора для витягу даних з DOM
            data = self._extract_raw_data(extractor)							        # 📥 Витяг сирих даних (title, price, description тощо)
            processed_data = await self._process_data(data)						        # ✨ Обробка: fallback + вага
            return self._build_product_info(processed_data)						        # 🏗️ Формування об'єкта ProductInfo

        except Exception as e:
            logging.exception(f"❌ Помилка при парсингу {self.url}: {e}")
            return ProductInfo(
                title="Помилка", price=0.0, description="Не вдалося отримати дані"
                )
        
    # ================================
    # 🧱 ДОПОМІЖНІ ПРИВАТНІ МЕТОДИ
    # ================================
    async def _fetch_and_prepare_soup(self) -> None:
        """
        🌐 Завантажує HTML-сторінку і створює BeautifulSoup дерево.
        """
        logging.info(f"🌍 Завантаження: {self.url}...")										    # 🧾 Лог про початок завантаження
        task_description = f"Завантаження [cyan]{self.url.split('/')[-1]}[/cyan]..."			# 📝 Опис для прогрес-бару

        if self.enable_progress:
            with Progress(SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(), transient=True
                    ) as progress:

                progress.add_task(description=task_description, total=None)							# ⏳ Додаємо завдання до прогрес-бара
                self.page_source = await self.webdriver_service.fetch_page_source(self.url)			# 🌐 Завантаження HTML через WebDriver

        else:
            self.page_source = await self.webdriver_service.fetch_page_source(self.url)				# 🌐 Без прогрес-бара

        if self.page_source:
            self._page_soup = BeautifulSoup(self.page_source, "html.parser")						# 🧽 Парсинг HTML у DOM-дерево
            logging.info(f"✅ Завантажено ({len(self.page_source)} байт).")						    # 🧾 Лог про успішне завантаження
        else:
            logging.error(f"❌ Неможливо завантажити: {self.url}")								    # ❗ Помилка при завантаженні

    def _extract_raw_data(self, extractor: HtmlDataExtractor) -> Dict[str, Any]:
        """
        📥 Витягує усі сирі дані з DOM-дерева.
        """
        return {
            "title": extractor.extract_title(),												        # 🏷️ Назва товару
            "price": extractor.extract_price(),												        # 💰 Ціна
            "description": extractor.extract_description(),									        # 📝 Опис товару
            "main_image": extractor.extract_main_image(),									        # 🖼️ Головне зображення
            "all_images": extractor.extract_all_images(),									        # 🖼️📁 Всі зображення
            "sections": extractor.extract_detailed_sections(),								        # 📚 Блоки опису
            "stock_data": self._get_stock_with_fallback(extractor),							        # 🗃️ Дані про наявність (stock)
        }

    async def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✨ Обробляє сирі дані: fallback опису + визначення ваги.
        """
        if data.get("description") and len(data["description"].strip()) < 20:						# 🧐 Якщо опис занадто короткий
            first_key = next(iter(data.get("sections", {})), None)
            if first_key:
                data["description"] = data["sections"][first_key]								    # 🔁 Використовуємо перший блок як опис

        title = data.get("title", "")
        description = data.get("description", "")
        image_url = data.get("main_image", "")
        data["weight"] = await self.weight_resolver.resolve(title, description, image_url)		    # ⚖️ AI-оцінка ваги товару

        return data

    def _build_product_info(self, data: Dict[str, Any]) -> ProductInfo:
        """
        🏗️ Збирає остаточний об'єкт ProductInfo з оброблених даних.
        """
        stock_data = data.get("stock_data", {})
        if stock_data:
            stock_data = self._map_stock_sizes(stock_data)										    # 🔄 Нормалізація назв розмірів

        return ProductInfo(
            title=data.get("title", "Невідомо"),											        # 🏷️ Назва
            price=float(data.get("price", 0.0)),											        # 💰 Ціна
            description=data.get("description", ""),										        # 📝 Опис
            image_url=data.get("main_image", ""),										            # 🖼️ Головне зображення
            weight=float(data.get("weight", 0.0)),										            # ⚖️ Вага
            images=data.get("all_images", []),											            # 🖼️📁 Всі зображення
            currency=self._currency,														        # 💱 Валюта (визначена з URL)
            sections=data.get("sections", {}),											            # 📚 Детальні блоки опису
            stock_data=stock_data,														            # 🗃️ Наявність по кольорах і розмірах
        )

    # ================================
    # 📦 ОБРОБКА НАЯВНОСТІ
    # ================================
    def _get_stock_with_fallback(self, extractor: HtmlDataExtractor) -> Dict[str, Dict[str, bool]]:
        """
        🗃️ Витягує наявність із JSON-LD або legacy DOM.
        """
        return extractor.extract_stock_from_json_ld() or extractor.extract_stock_from_legacy() or {}	# 🔁 Fallback логіка

    def _map_stock_sizes(self, stock_data: Dict[str, Dict[str, bool]]) -> Dict[str, Dict[str, bool]]:
        """
        🔄 Приводить сирі розміри до стандартного формату ("XSmall" → "XS").
        """
        return {
            color: {
                self._map_size(size): available												# ↔️ Мапінг кожного розміру
                for size, available in sizes.items()
            }
            for color, sizes in stock_data.items()
        }

    def _map_size(self, raw_size: str) -> str:
        """
        🔤 Маппінг одного розміру у короткий вигляд.
        """
        size_mapping = {
            "XXSmall": "XXS", "XSmall": "XS", "Small": "S", "Medium": "M",
            "Large": "L", "XLarge": "XL", "XXLarge": "XXL", "XXXLarge": "XXXL"
        }
        clean_size = re.sub(r"[^a-zA-Z]", "", raw_size)									    # 🧹 Видаляємо зайві символи (наприклад, пробіли)
        return size_mapping.get(clean_size, clean_size)										# 🧭 Повертаємо мапінг або оригінал