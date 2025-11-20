# 🧰 app/infrastructure/services/product_media_preparer.py
"""
🧰 Підготовка стеку медіа для карток товару.

🔹 Викачує всі URL зображень із ретраями через `ImageDownloader`.
🔹 Перевіряє, що стек не порожній, і повертає готові `InputFile`.
🔹 Будь-яка помилка (битий URL, таймаут, невалідний контент) → `ProductMediaPreparationError`.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from telegram import InputFile

# 🔠 Системні імпорти
import io
import logging
import os
from dataclasses import dataclass
from typing import Final, List, Sequence
from urllib.parse import urlparse

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.size_chart.image_downloader import ImageDownloader
from app.shared.utils.logger import LOG_NAME

logger: Final = logging.getLogger(f"{LOG_NAME}.media_preparer")


class ProductMediaPreparationError(RuntimeError):
    """❌ Помилка підготовки стеку медіа."""


@dataclass(slots=True)
class PreparedMediaStack:
    """📦 Результат підготовки стеку фото."""

    files: List[InputFile]


class ProductMediaPreparer:
    """Готує стек фотографій до надсилання у Telegram."""

    def __init__(
        self,
        downloader: ImageDownloader,
        *,
        max_images: int = 10,
    ) -> None:
        self._downloader = downloader
        self._max_images = max(1, int(max_images))

    async def prepare_stack(self, urls: Sequence[str], *, title: str | None = None) -> PreparedMediaStack:
        """Завантажує всі зображення та повертає список `InputFile`."""
        unique_urls = self._normalize_urls(urls)
        if not unique_urls:
            raise ProductMediaPreparationError("Список зображень порожній або невалідний.")

        prepared_files: List[InputFile] = []
        for idx, img_url in enumerate(unique_urls, start=1):
            try:
                image_data = await self._downloader.fetch(img_url)
            except Exception as exc:  # noqa: BLE001
                name = title or f"#{idx}"
                logger.warning("🖼️ Не вдалося завантажити фото %s (%s): %s", idx, name, exc)
                raise ProductMediaPreparationError(f"Не вдалося завантажити фото #{idx}: {exc}") from exc

            buffer = io.BytesIO(image_data.content)
            filename = self._build_filename(img_url, idx, image_data.content_type)
            prepared_files.append(
                InputFile(
                    buffer,
                    filename=filename,
                    attach=True,  # 📎 Потрібно для media group (attach://)
                )
            )

        logger.debug("🖼️ Готово %d фото для: %s", len(prepared_files), (title or "N/A"))
        return PreparedMediaStack(files=prepared_files)

    def _normalize_urls(self, urls: Sequence[str]) -> List[str]:
        seen: set[str] = set()
        result: List[str] = []
        for raw in urls or []:
            candidate = (raw or "").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            result.append(candidate)
            if len(result) >= self._max_images:
                break
        return result

    @staticmethod
    def _build_filename(url: str, idx: int, content_type: str | None) -> str:
        parsed = urlparse(url)
        basename = os.path.basename(parsed.path or "") or f"image_{idx}"
        ext = os.path.splitext(basename)[1]
        if not ext and content_type:
            ext = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }.get(content_type.lower(), "")
        if not ext.startswith("."):
            ext = f".{ext.lstrip('.')}" if ext else ".jpg"
        safe_name = basename or f"image_{idx}"
        if not safe_name.endswith(ext):
            safe_name = f"{safe_name}{ext}"
        return safe_name


__all__ = [
    "PreparedMediaStack",
    "ProductMediaPreparer",
    "ProductMediaPreparationError",
]
