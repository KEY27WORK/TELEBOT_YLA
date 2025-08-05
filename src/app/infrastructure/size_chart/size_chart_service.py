# 📏 app/infrastructure/size_chart/size_chart_service.py
"""
📏 size_chart_service.py — Сервіс-оркестратор для обробки таблиць розмірів.
"""

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup                                          # 🧽 HTML-парсинг

# 🔠 Системні імпорти
import logging                                                         # 🧾 Логування
import time                                                            # ⏱ Вимірювання часу
from typing import List, Tuple, Dict                                   # 🧰 Типізація
from pathlib import Path                                               # 📁 Робота з директоріями

# 🧩 Внутрішні модулі проєкту
from .image_downloader import ImageDownloader                         # 🖼️ Завантаження зображень
from .ocr_service import OCRService                                   # 🔎 OCR-розпізнавання
from app.infrastructure.image_generation.table_generator_factory import TableGeneratorFactory  # 🏗️ Генератор таблиць
from app.shared.utils.prompts import ChartType                        # 📊 Тип таблиці
from app.shared.utils.logger import LOG_NAME                          # 🧾 Імʼя логгера


# ================================
# 📏 СЕРВІС ОБРОБКИ ТАБЛИЦЬ РОЗМІРІВ
# ================================
logger = logging.getLogger(LOG_NAME)

class SizeChartService:
    """ 📏 Обробляє HTML: знаходить, розпізнає та генерує таблиці розмірів. """

    def __init__(
        self,
        downloader: ImageDownloader,
        ocr_service: OCRService,
        generator_factory: TableGeneratorFactory
    ):
        self.downloader = downloader										# 🖼️ Сервіс для завантаження зображень
        self.ocr_service = ocr_service									# 🔎 Сервіс розпізнавання тексту на зображеннях
        self.generator_factory = generator_factory							# 🏗️ Фабрика генераторів таблиць

    # ================================
    # 🔎 ПОШУК ЗОБРАЖЕНЬ У HTML
    # ================================
    def _find_size_chart_images(self, page_source: str) -> List[Tuple[str, ChartType]]:
        """ 🔎 Шукає всі зображення таблиць розмірів у HTML. """
        logger.info("🔎 Пошук зображень таблиць розмірів у HTML...")
        soup = BeautifulSoup(page_source, "html.parser")						# 🧽 Розпарсимо HTML у дерево
        blocks = soup.select(".product-info__block-item")						# 🔍 Шукаємо потрібні блоки

        found_images: List[Tuple[str, ChartType]] = []
        used_urls = set()

        for block in blocks:
            for img in block.select("img"):
                src_attr = img.get("src")

                if not isinstance(src_attr, str) or not src_attr:						# ❗ Пропускаємо невалідні посилання
                    continue

                src = src_attr
                full_url = f"https:{src}" if src.startswith("//") else src			# 🔗 Уточнюємо повну URL-адресу

                if full_url in used_urls:
                    continue
                used_urls.add(full_url)

                src_lower = src.lower()
                if any(k in src_lower for k in ["size_chart", "size-chart", "sizechart", "_size_", "size_"]):
                    found_images.append((full_url, ChartType.UNIQUE))				# 🧩 Унікальна таблиця
                elif "women-size-chart" in src_lower or "size_chart_top_jogger_" in src_lower:
                    found_images.append((full_url, ChartType.GENERAL))				# 🧩 Стандартна таблиця

        logger.info(f"🔢 Знайдено {len(found_images)} зображень таблиць розмірів.")
        return found_images

    # ================================
    # 🚀 ПОВНИЙ ЦИКЛ ОБРОБКИ
    # ================================
    async def process_all_size_charts(self, page_source: str) -> List[str]:
        """ 🚀 Повний цикл: знаходить, завантажує, розпізнає та генерує таблиці. """
        if not page_source:
            logger.warning("⚠️ Передано порожній page_source, обробку скасовано.")
            return []

        start_time = time.time()									# ⏱ Починаємо замір часу
        images_to_process = self._find_size_chart_images(page_source)				# 🔎 Шукаємо таблиці
        if not images_to_process:
            return []

        results: List[str] = []
        temp_dir = Path("temp_size_charts")
        temp_dir.mkdir(exist_ok=True)									# 📁 Створюємо тимчасову директорію

        for index, (img_url, chart_type) in enumerate(images_to_process):
            downloaded_path = await self.downloader.download(img_url, temp_dir / f"download_{index}.png")	# ⬇️ Завантажуємо зображення
            if not downloaded_path:
                continue

            recognized_data = await self.ocr_service.recognize(str(downloaded_path), chart_type)		# 🔍 OCR-розпізнавання
            if not recognized_data:
                continue

            generated_path = str(temp_dir / f"generated_{index}.png")							# 📍 Куди зберегти результат
            generator = self.generator_factory.create_generator(
                chart_type, recognized_data, generated_path
            )

            if result_path := await generator.generate():								# 🖼️ Генеруємо фінальну картинку
                results.append(result_path)

        elapsed = time.time() - start_time									# ⏱ Підраховуємо час виконання
        logger.info(f"✅ Оброблено {len(results)} таблиць за {elapsed:.2f} сек.")
        return results