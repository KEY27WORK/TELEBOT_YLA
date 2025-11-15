# 📏 app/infrastructure/size_chart/__init__.py
"""
📏 Інфраструктурний модуль повного циклу роботи з таблицями розмірів.

🔹 Downloader (`ImageDownloader`) — завантаження зображень таблиць.
🔹 OCR (`OCRService`) — розпізнавання та нормалізація даних.
🔹 Генерація (`TableGeneratorFactory`) — побудова PNG/зображень.
🔹 Оркестрація (`SizeChartService`) — координує pipeline + прогрес.
🔹 Пошук (`YoungLASizeChartFinder`) — знаходить таблиці на сторінках.
"""

from __future__ import annotations

# 📥 Downloader
from .image_downloader import DownloadError, DownloadOutcome, DownloadResult, ImageDownloader

# 📄 DTO + OCR
from .dto import SizeChartOcrResult, SizeChartOcrStatus
from .ocr_service import OCRService

# 🛠️ Генерація зображень
from .table_generator_factory import TableGeneratorFactory

# 🧭 Оркестрація процесу
from .size_chart_service import ProgressCallback, SizeChartProgress, SizeChartService, Stage

# 🔍 Пошук таблиць на сторінці
from .youngla_finder import YoungLASizeChartFinder

__all__ = [
    "DownloadError",
    "DownloadOutcome",
    "DownloadResult",
    "ImageDownloader",
    "OCRService",
    "SizeChartOcrResult",
    "SizeChartOcrStatus",
    "TableGeneratorFactory",
    "ProgressCallback",
    "SizeChartProgress",
    "SizeChartService",
    "Stage",
    "YoungLASizeChartFinder",
]
