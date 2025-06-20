"""
📏 size_chart_handler.py — обробка таблиць розмірів для Telegram-бота YoungLA Ukraine.

🔹 Клас `SizeChartHandler`:
- Завантажує HTML-сторінку за посиланням.
- Витягує зображення таблиці розмірів.
- Виконує OCR-розпізнавання.
- Генерує структуровану таблицю у вигляді зображення.

✅ Принципи:
- SRP — кожен метод виконує єдину функцію.
- DIP — залежності передаються через інʼєкцію (OCRService, ImageDownloader).
- OCP — підтримка нових типів таблиць без зміни логіки.
"""

# 🧱 Системні
import logging
import time
from typing import Optional, Dict, Tuple, List
from bs4 import BeautifulSoup

# 🌐 WebDriver
from core.webdriver.webdriver_service import WebDriverService

# 🧰 OCR і генератори
from .image_downloader import ImageDownloader
from .ocr_service import OCRService
from .table_generator import GeneralTableGenerator, UniqueTableGenerator


class SizeChartHandler:
    def __init__(
        self,
        url: str,
        page_source: Optional[str] = None,
        model: str = "gpt-4-turbo",
        downloader: Optional[ImageDownloader] = None,
        ocr_service: Optional[OCRService] = None,
    ):
        self.url = url
        self.page_source = page_source
        self.image_path = "size_chart.png"
        self.web_driver = WebDriverService() if not page_source else None
        self.downloader = downloader or ImageDownloader(self.image_path)
        self.ocr_service = ocr_service or OCRService(model)

    def find_size_chart_in_html(self, html: str) -> Optional[Tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        images = soup.select("img")

        found_unique = []
        general_size_chart = None
        grid_size_chart = None

        for img in images:
            img_src = img.get("src", "")
            if any(k in img_src for k in ["size_chart", "Size-Chart", "SizeChart", "SIZE_CHART", "SIZECHART", "_size_", "size_", "_size"]):
                full_url = f"https:{img_src}" if img_src.startswith("//") else img_src
                found_unique.append(full_url)
            elif "women-size-chart" in img_src:
                general_size_chart = f"https:{img_src}" if img_src.startswith("//") else img_src
            elif "Size_Chart_TOP_JOGGER_" in img_src:
                grid_size_chart = f"https:{img_src}" if img_src.startswith("//") else img_src

        if found_unique:
            logging.info(f"✅ Знайдено {len(found_unique)} унікальних таблиць")
            return found_unique[0], "unique-size-chart"
        elif grid_size_chart:
            logging.info(f"✅ Знайдена таблиця зріст-вага: {grid_size_chart}")
            return grid_size_chart, "grid-size-chart"
        elif general_size_chart:
            logging.info(f"✅ Знайдена загальна жіноча таблиця: {general_size_chart}")
            return general_size_chart, "general-size-chart"

        return None

    def get_size_chart_image(self) -> Optional[Tuple[str, str]]:
        logging.info(f"🔎 Пошук таблиці розмірів: {self.url}")
        attempts = 5

        for attempt in range(1, attempts + 1):
            logging.info(f"🔄 Спроба {attempt}/{attempts}...")

            if self.page_source:
                result = self.find_size_chart_in_html(self.page_source)
                if result:
                    logging.info(f"✅ Таблиця знайдена в HTML (спроба {attempt})")
                    return result

            if not self.page_source:
                self.page_source = self.web_driver.fetch_page_source(self.url)

            if self.page_source:
                result = self.find_size_chart_in_html(self.page_source)
                if result:
                    logging.info(f"✅ Таблиця знайдена після завантаження (спроба {attempt})")
                    return result

            if attempt < attempts:
                logging.warning("⚠️ Таблиця не знайдена. Оновлюю сторінку...")
                self.web_driver.refresh_page()
                time.sleep(2)

        logging.error("❌ Таблиця розмірів не знайдена після всіх спроб.")
        return None

    def _get_generator(self, chart_type: str, size_chart: Dict[str, List], output_path: str):
        if chart_type == "unique-size-chart":
            return UniqueTableGenerator(size_chart, output_path)
        return GeneralTableGenerator(size_chart, output_path)

    async def process_size_chart(self) -> Optional[str]:
        charts = await self.process_all_size_charts()
        return charts[0] if charts else None

    def get_all_size_chart_images(self) -> List[Tuple[str, str]]:
        logging.info(f"🔎 Пошук усіх таблиць розмірів: {self.url}")
        if not self.page_source:
            self.page_source = self.web_driver.fetch_page_source(self.url)

        soup = BeautifulSoup(self.page_source, "html.parser")
        blocks = soup.select(".product-info__block-item")

        found_images = []
        used_urls = set()

        for block in blocks:
            images = block.select("img")
            for img in images:
                src = img.get("src", "")
                full_url = f"https:{src}" if src.startswith("//") else src

                if full_url in used_urls:
                    continue
                used_urls.add(full_url)

                if any(k in src for k in ["size_chart", "Size-Chart", "SizeChart", "SIZE_CHART", "SIZECHART", "_size_", "size_", "_size"]):
                    found_images.append((full_url, "unique-size-chart"))
                elif "women-size-chart" in src:
                    found_images.append((full_url, "general-size-chart"))
                elif "Size_Chart_TOP_JOGGER_" in src:
                    found_images.append((full_url, "grid-size-chart"))

        logging.info(f"🔢 Знайдено {len(found_images)} таблиць (без general-size-chart)")
        return found_images

    async def process_all_size_charts(self) -> List[str]:
        start_time = time.time()
        logging.info("🚀 Обробка ВСІХ таблиць розмірів...")

        size_charts = self.get_all_size_chart_images()
        if not size_charts:
            return []

        results = []

        for index, (img_url, chart_type) in enumerate(size_charts):
            numbered_path = f"size_chart_{index}.png"
            self.downloader.image_path = numbered_path
            if not self.downloader.download(img_url):
                continue

            size_chart = self.ocr_service.recognize(numbered_path, chart_type)
            if not size_chart:
                continue

            generated_path = f"generated_size_chart_{index}.png"
            generator = self._get_generator(chart_type, size_chart, generated_path)
            result_path = await generator.generate()

            if result_path:
                results.append(result_path)

        logging.info(f"✅ Оброблено {len(results)} з {len(size_charts)} за {time.time() - start_time:.2f} сек.")
        return results
