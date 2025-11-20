# 🪧 app/infrastructure/services/banner_drop_service.py
"""
🪧 BannerDropService — автоматизує сценарій Poster/Banner drop для головної сторінки YoungLA.

Кроки:
1. Завантажує HTML через WebDriverService.
2. Шукає банерні слайди з посиланнями на колекції.
3. Скачує банер, ріже на три вертикальні частини.
4. Збирає назви товарів з наявних колекцій та генерує текст через AI.
5. Надсилає альбом у Telegram й запускає стандартний режим парсингу колекцій.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from bs4 import BeautifulSoup                                                     # 🥣 HTML-парсинг
from PIL import Image                                                             # 🖼️ Робота з банером
from telegram import InputFile, Update                                            # 🤖 Telegram об'єкти
from telegram.helpers import escape_markdown                                      # 🔐 Екранування markdown

# 🔠 Системні імпорти
import asyncio                                                                     # ⏱️ Контроль одночасних запусків
import html                                                                        # 🔐 Екранування HTML
import logging                                                                     # 🧾 Логування сервісу
from collections import deque                                                     # ♻️ Простий LRU для банерів
from dataclasses import dataclass                                                 # 🧱 DTO для знайдених банерів
from io import BytesIO                                                            # 💾 Робота з байтами зображення
from typing import Deque, List, Optional, Sequence, Set                           # 🧰 Типи
from urllib.parse import urljoin                                                  # 🌐 Побудова абсолютних URL

# 🧩 Внутрішні модулі проєкту
from app.bot.handlers.product.collection_handler import CollectionHandler         # 🧺 Стандартний обробник колекцій
from app.bot.handlers.product.image_sender import ImageSender                     # 🖼️ Надсилання медіагруп
from app.bot.services.custom_context import CustomContext                         # 🧠 Контекст PTB
from app.bot.ui import static_messages as msg                                     # 💬 Статичні повідомлення
from app.config.setup.constants import AppConstants                               # ⚙️ Константи застосунку
from app.errors.exception_handler_service import ExceptionHandlerService          # 🛡️ Обробка виключень
from app.infrastructure.ai.ai_task_service import AITaskService                   # 🤖 Генератор текстів
from app.infrastructure.collection_processing.collection_processing_service import (
    CollectionProcessingService,
)                                                                                 # 📚 Збір URL товарів
from app.infrastructure.services.product_processing_service import (              # 🧠 Дані про товари
    ProductProcessingService,
)
from app.infrastructure.size_chart.image_downloader import ImageDownloader        # 📥 Завантаження зображень
from app.infrastructure.web.webdriver_service import WebDriverService             # 🌐 Завантаження HTML
from app.shared.utils.logger import LOG_NAME                                      # 🏷️ Базовий логер
from app.shared.utils.url_parser_service import UrlParserService                  # 🔗 Нормалізація URL

logger = logging.getLogger(f"{LOG_NAME}.banner_drop")                            # 🧾 Логер сервісу


# ================================
# 🧱 DTO
# ================================
@dataclass(slots=True)
class BannerCandidate:
    """Розпізнаний банер із корисними даними."""

    image_url: str
    collection_links: List[str]
    label: str
    button_labels: List[str]


# ================================
# 🪧 ОСНОВНИЙ СЕРВІС
# ================================
class BannerDropService:
    """Координує повний цикл Poster-drop на головній YoungLA."""

    def __init__(
        self,
        *,
        webdriver_service: WebDriverService,
        url_parser_service: UrlParserService,
        collection_processing_service: CollectionProcessingService,
        product_processing_service: ProductProcessingService,
        ai_service: AITaskService,
        image_downloader: ImageDownloader,
        image_sender: ImageSender,
        collection_handler: CollectionHandler,
        constants: AppConstants,
        exception_handler: ExceptionHandlerService,
        max_product_titles: int = 9,
        processed_cache_size: int = 5,
    ) -> None:
        self._webdriver = webdriver_service
        self._url_parser = url_parser_service
        self._collection_processing = collection_processing_service
        self._product_processing = product_processing_service
        self._ai_service = ai_service
        self._image_downloader = image_downloader
        self._image_sender = image_sender
        self._collection_handler = collection_handler
        self._constants = constants
        self._exception_handler = exception_handler
        self._max_titles = max(1, int(max_product_titles))
        self._cache_limit = max(1, int(processed_cache_size))
        self._processed_queue: Deque[str] = deque()
        self._processed_lookup: Set[str] = set()
        self._lock = asyncio.Lock()
        self._default_home = "https://www.youngla.com/"
        logger.info(
            "🪧 banner_drop.init",
            extra={"max_titles": self._max_titles, "cache_limit": self._cache_limit},
        )

    # ================================
    # 📬 ПУБЛІЧНИЙ API
    # ================================
    async def process_homepage(
        self,
        *,
        update: Update,
        context: CustomContext,
        url: Optional[str] = None,
    ) -> None:
        """Обробляє головну сторінку та надсилає банерний пост користувачу."""
        if update is None or context is None:
            raise ValueError("update та context обов'язкові для BannerDropService")

        parse_mode = getattr(getattr(self._constants, "UI", object()), "DEFAULT_PARSE_MODE", None)
        message = update.effective_message
        target_url = self._normalize_home_url(url)

        async with self._lock:
            try:
                if message:
                    await message.reply_text(msg.BANNER_DROP_IN_PROGRESS, parse_mode=parse_mode)
                html = await self._webdriver.get_page_content(target_url, wait_until="networkidle")
                if not html:
                    if message:
                        await message.reply_text(msg.BANNER_DROP_FAILED, parse_mode=parse_mode)
                    logger.warning("🪧 banner_drop.empty_page", extra={"url": target_url})
                    return

                candidates = self._extract_banners(html, base_url=target_url)
                logger.info("🪧 banner_drop.found", extra={"count": len(candidates)})
                processed_any = False
                for candidate in candidates:
                    if self._is_cached(candidate.image_url):
                        logger.debug("🪧 banner_drop.skip_cached", extra={"image": candidate.image_url})
                        continue
                    handled = await self._handle_candidate(candidate, update, context, parse_mode)
                    if handled:
                        self._remember_banner(candidate.image_url)
                        processed_any = True

                if not processed_any and message:
                    await message.reply_text(msg.BANNER_DROP_NO_NEW, parse_mode=parse_mode)
            except asyncio.CancelledError:
                logger.warning("🪧 banner_drop.cancelled")
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("🔥 banner_drop.failed")
                await self._exception_handler.handle(exc, update)
                if message:
                    await message.reply_text(msg.BANNER_DROP_FAILED, parse_mode=parse_mode)

    # ================================
    # 🔧 ДОПОМІЖНІ МЕТОДИ
    # ================================
    async def _handle_candidate(
        self,
        candidate: BannerCandidate,
        update: Update,
        context: CustomContext,
        parse_mode: Optional[str],
    ) -> bool:
        try:
            image_data = await self._image_downloader.fetch(candidate.image_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("🪧 banner_drop.image_failed", extra={"url": candidate.image_url, "error": str(exc)})
            return False

        media_group = self._slice_banner(image_data.content)
        if not media_group:
            logger.warning("🪧 banner_drop.slice_empty", extra={"url": candidate.image_url})
            return False

        product_titles = await self._collect_product_titles(candidate.collection_links)
        if not product_titles:
            logger.warning("🪧 banner_drop.products_empty", extra={"links": len(candidate.collection_links)})

        try:
            caption_body = await self._ai_service.generate_banner_post(
                collection_label=candidate.label or "YoungLA drop",
                product_names=product_titles or ["YoungLA essentials"],
                vibe_hint=" / ".join(filter(None, candidate.button_labels)) or candidate.label,
                link_count=len(candidate.collection_links),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("🪧 banner_drop.ai_failed", extra={"error": str(exc)})
            caption_body = "YoungLA drop на головній. Забирай образ та замовляй зараз!"

        caption = self._format_caption(caption_body, product_titles, parse_mode)
        await self._image_sender.send_images(
            update,
            context,
            images=media_group,
            caption=caption,
            parse_mode=parse_mode,
        )
        await self._run_collection_handlers(update, context, candidate.collection_links)
        return True

    async def _collect_product_titles(self, collection_links: Sequence[str]) -> List[str]:
        titles: List[str] = []
        seen_products: Set[str] = set()
        for link in collection_links:
            try:
                product_links = await self._collection_processing.get_product_links(link)
            except Exception as exc:  # noqa: BLE001
                logger.warning("🪧 banner_drop.collection_failed", extra={"url": link, "error": str(exc)})
                continue

            for product_url in product_links:
                url_value = getattr(product_url, "value", str(product_url))
                if url_value in seen_products:
                    continue
                seen_products.add(url_value)
                try:
                    result = await self._product_processing.process_url(url_value)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("🪧 banner_drop.product_failed", extra={"url": url_value, "error": str(exc)})
                    continue
                if not result.ok or not result.data or not result.data.content:
                    continue
                title = getattr(result.data.content, "title", "")
                if title:
                    titles.append(title.strip())
                if len(titles) >= self._max_titles:
                    return titles
        return titles

    async def _run_collection_handlers(
        self, update: Update, context: CustomContext, links: Sequence[str]
    ) -> None:
        modes = getattr(getattr(self._constants, "LOGIC", object()), "MODES", object())
        collection_mode = getattr(modes, "COLLECTION", "collection")
        for link in links:
            try:
                context.mode = collection_mode
                context.url = link
                await self._collection_handler.handle_collection(update, context, url=link)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("🪧 banner_drop.collection_handler_failed", extra={"url": link, "error": str(exc)})

    def _extract_banners(self, html: str, base_url: str) -> List[BannerCandidate]:
        soup = BeautifulSoup(html, "lxml")
        containers = list(soup.select("slideshow-carousel .slideshow__slide"))
        containers += soup.select("[data-section-type*=banner] .content-over-media")
        containers += soup.select("section .content-over-media")

        seen_images: Set[str] = set()
        candidates: List[BannerCandidate] = []
        for node in containers:
            image_url = self._extract_image_url(node, base_url)
            if not image_url or image_url in seen_images:
                continue
            links = self._extract_collection_links(node, base_url)
            if not links:
                continue
            label = self._extract_label(node)
            buttons = [btn.get_text(strip=True) for btn in node.select(".button") if btn.get_text(strip=True)]
            candidates.append(BannerCandidate(image_url=image_url, collection_links=links, label=label, button_labels=buttons))
            seen_images.add(image_url)
        return candidates

    def _extract_image_url(self, node: object, base_url: str) -> Optional[str]:
        tag = node.find("img") if hasattr(node, "find") else None  # type: ignore[attr-defined]
        attrs = ("data-src", "data-original", "src", "data-zoom-image")
        raw_url: Optional[str] = None
        if tag is not None:
            for attr in attrs:
                raw_url = tag.get(attr)  # type: ignore[attr-defined]
                if raw_url:
                    break
        if not raw_url and hasattr(node, "find"):
            source = node.find("source")  # type: ignore[attr-defined]
            if source is not None:
                raw_url = source.get("srcset")  # type: ignore[attr-defined]
                if raw_url and " " in raw_url:
                    raw_url = raw_url.split()[0]
        return self._normalize_link(base_url, raw_url)

    def _extract_collection_links(self, node: object, base_url: str) -> List[str]:
        if not hasattr(node, "select"):
            return []
        links: List[str] = []
        seen: Set[str] = set()
        for anchor in node.select("a[href]"):
            href = anchor.get("href")  # type: ignore[attr-defined]
            normalized = self._normalize_link(base_url, href)
            if not normalized or normalized in seen:
                continue
            if "/collections/" not in normalized and not self._url_parser.is_collection_url(normalized):
                continue
            links.append(normalized)
            seen.add(normalized)
        return links

    @staticmethod
    def _extract_label(node: object) -> str:
        if hasattr(node, "select_one"):
            content = node.select_one(".slideshow__slide-content") or node.select_one(".content-over-media__content")
            if content is not None:
                text = content.get_text(" ", strip=True)  # type: ignore[attr-defined]
                return text[:200]
        if hasattr(node, "get_text"):
            return node.get_text(" ", strip=True)[:200]  # type: ignore[attr-defined]
        return ""

    def _slice_banner(self, raw_bytes: bytes) -> List[InputFile]:
        try:
            with Image.open(BytesIO(raw_bytes)) as banner:
                width, height = banner.size
                fmt = (banner.format or "JPEG").upper()
                target_format = "PNG" if fmt == "PNG" else "JPEG"
                media: List[InputFile] = []
                for idx in range(3):
                    left = round(width * idx / 3)
                    right = round(width * (idx + 1) / 3)
                    if right <= left:
                        right = min(width, left + 1)
                    crop = banner.crop((left, 0, right, height))
                    if target_format == "JPEG" and crop.mode in {"RGBA", "P"}:
                        crop = crop.convert("RGB")
                    buffer = BytesIO()
                    save_format = target_format
                    params = {"format": save_format}
                    if save_format == "JPEG":
                        params["quality"] = 90
                    crop.save(buffer, **params)
                    buffer.seek(0)
                    ext = "png" if save_format == "PNG" else "jpg"
                    media.append(InputFile(buffer, filename=f"banner_{idx + 1}.{ext}"))
                return media
        except Exception as exc:  # noqa: BLE001
            logger.warning("🪧 banner_drop.slice_fail", extra={"error": str(exc)})
            return []

    @staticmethod
    def _normalize_home_url(raw: Optional[str]) -> str:
        candidate = (raw or "https://www.youngla.com/").strip()
        if not candidate.startswith("http://") and not candidate.startswith("https://"):
            candidate = f"https://{candidate.lstrip('/')}"
        return candidate

    def _normalize_link(self, base_url: str, href: Optional[str]) -> Optional[str]:
        if not href:
            return None
        cleaned = href.strip()
        if cleaned.startswith("//"):
            cleaned = f"https:{cleaned}"
        absolute = urljoin(base_url, cleaned)
        try:
            normalized = self._url_parser.normalize(absolute)  # type: ignore[attr-defined]
        except Exception:
            normalized = absolute.strip()
        return normalized or None

    def _format_caption(
        self, caption_body: str, products: Sequence[str], parse_mode: Optional[str]
    ) -> str:
        text = caption_body.strip() if caption_body else "YoungLA drop."
        lines = [text]
        if products:
            lines.append("")
            lines.append("В колекції:")
            lines.extend(f"• {name}" for name in products)
        caption = "\n".join(line for line in lines if line is not None)
        if not parse_mode:
            return caption
        upper = str(parse_mode).upper()
        if upper == "HTML":
            return html.escape(caption)
        if upper.startswith("MARKDOWN"):
            return escape_markdown(caption, version=2)
        return caption

    def _remember_banner(self, image_url: str) -> None:
        self._processed_queue.append(image_url)
        self._processed_lookup.add(image_url)
        while len(self._processed_queue) > self._cache_limit:
            dropped = self._processed_queue.popleft()
            self._processed_lookup.discard(dropped)

    def _is_cached(self, image_url: str) -> bool:
        return image_url in self._processed_lookup


__all__ = ["BannerDropService"]
