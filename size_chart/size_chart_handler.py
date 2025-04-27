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
    """📊 Клас для обробки таблиць розмірів із сайту."""

    def __init__(
        self,
        url: str,
        page_source: Optional[str] = None,
        model: str = "gpt-4-turbo",
        downloader: Optional[ImageDownloader] = None,
        ocr_service: Optional[OCRService] = None
    ):
        """
        Ініціалізує обробник.

        :param url: Посилання на товар.
        :param page_source: HTML-код сторінки (якщо вже завантажено).
        :param model: Модель GPT для OCR (default: gpt-4-turbo).
        :param downloader: Інʼєкція ImageDownloader.
        :param ocr_service: Інʼєкція OCRService.
        """
        self.url = url
        self.page_source = page_source
        self.image_path = "size_chart.png"
        self.web_driver = WebDriverService() if not page_source else None
        self.downloader = downloader or ImageDownloader(self.image_path)
        self.ocr_service = ocr_service or OCRService(model)

    def get_size_chart_image(self) -> Optional[Tuple[str, str]]:
        """
        🔍 Пошук таблиці розмірів по HTML/URL.

        :return: Кортеж (url_зображення, тип таблиці), або None.
        """
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

    def find_size_chart_in_html(self, html: str) -> Optional[Tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        images = soup.select("img")
    
        unique_size_chart = None
        general_size_chart = None
        grid_size_chart = None
     
        for img in images:
            img_src = img.get("src", "")
            if "size_chart" in img_src or "Size-Chart" in img_src or "SizeChart" in img_src or "SIZE_CHART" in img_src or "SIZECHART" in img_src:
                unique_size_chart = f"https:{img_src}" if img_src.startswith("//") else img_src
                logging.info(f"✅ Знайдена унікальна таблиця розмірів: {unique_size_chart}")
            elif "women-size-chart" in img_src:
                general_size_chart = f"https:{img_src}" if img_src.startswith("//") else img_src
                logging.info(f"✅ Знайдена загальна жіноча таблиця: {general_size_chart}")
            elif "Size_Chart_TOP_JOGGER_" in img_src:
                grid_size_chart = f"https:{img_src}" if img_src.startswith("//") else img_src
                logging.info(f"✅ Знайдена таблиця зріст-вага: {grid_size_chart}")
            
            
    
        if unique_size_chart:
            return unique_size_chart, "unique-size-chart"
        elif grid_size_chart:
            return grid_size_chart, "grid-size-chart"
        elif general_size_chart:
            return general_size_chart, "general-size-chart"
    
        return None
    


    def _get_generator(self, chart_type: str, size_chart: Dict[str, List], output_path: str):
        """
        🧩 Вибирає відповідний генератор таблиці.

        :param chart_type: Тип (unique/general).
        :param size_chart: Розпізнані дані.
        :param output_path: Куди зберегти зображення.
        """
        if chart_type == "unique-size-chart":
            return UniqueTableGenerator(size_chart, output_path)
        return GeneralTableGenerator(size_chart, output_path)

    async def process_size_chart(self) -> Optional[str]:
        """
        📈 Повний цикл обробки таблиці:
        - Завантаження
        - OCR
        - Генерація зображення

        :return: Шлях до зображення або None.
        """
        start_time = time.time()
        logging.info("🚀 Початок обробки таблиці розмірів...")

        size_chart_data = self.get_size_chart_image()
        if not size_chart_data:
            return None

        img_url, chart_type = size_chart_data
        if not self.downloader.download(img_url):
            return None

        size_chart = self.ocr_service.recognize(self.image_path, chart_type)
        if not size_chart:
            return None

        generator = self._get_generator(chart_type, size_chart, "generated_size_chart.png")
        result = await generator.generate()

        logging.info(f"✅ Завершено за {time.time() - start_time:.2f} сек.")
        return result
