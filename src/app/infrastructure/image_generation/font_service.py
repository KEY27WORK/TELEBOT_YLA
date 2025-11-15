# 🔤 app/infrastructure/image_generation/font_service.py
"""
🔤 FontService — шукає та кешує шрифти для генерації зображень.

🔹 Підтримує пріоритет джерел: конфіг → assets → системні дефолти → Pillow fallback.
🔹 Кешує пари `(FontType, size)` у памʼяті, аби уникнути зайвих дискових звернень.
🔹 Надає утиліту для вимірювання ширини тексту вибраним шрифтом.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from PIL import Image, ImageDraw, ImageFont	# 🖼️ Робота зі шрифтами та вимірюваннями

# 🔠 Системні імпорти
import logging	# 🧾 Логування ініціалізації та fallback-ів
from pathlib import Path	# 📂 Операції з шляхами
from typing import Iterable, List, Optional, Sequence	# 🧰 Типізація

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService	# ⚙️ Конфігураційний сервіс
from app.domain.image_generation.interfaces import FontLike, FontType, IFontService	# ✍️ Доменні контракти
from app.shared.utils.logger import LOG_NAME	# 🏷️ Імʼя базового логера

# ================================
# 🧾 ЛОГЕР ТА КОНСТАНТИ
# ================================
logger = logging.getLogger(LOG_NAME)	# 🧾 Логер модуля

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"	# 📦 Корінь assets
FONTS_DIR = ASSETS_DIR / "fonts"	# 🗂️ Вбудовані шрифти

DEFAULT_BOLD_PATHS: Sequence[str] = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",	# 🐧 Linux
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",	# 🍎 macOS Arial
    "/System/Library/Fonts/Roboto-Bold.ttf",	# 🍎 macOS Roboto
    r"C:\Windows\Fonts\arialbd.ttf",	# 🪟 Arial Bold
    r"C:\Windows\Fonts\Roboto-Bold.ttf",	# 🪟 Roboto Bold
)
DEFAULT_MONO_PATHS: Sequence[str] = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",	# 🐧 Linux Mono
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",	# 🍎 Courier
    r"C:\Windows\Fonts\consola.ttf",	# 🪟 Consolas
    r"C:\Windows\Fonts\cour.ttf",	# 🪟 Courier New
)


# ================================
# 🏛️ СЕРВІС ШРИФТІВ
# ================================
class FontService(IFontService):
    """✍️ Реалізація `IFontService` із ручним кешем і багаторівневими fallback-ами."""

    def __init__(self, config_service: Optional[ConfigService] = None) -> None:
        """⚙️ Зчитує конфіг, формує списки пошуку та створює кеш/полотно."""
        self._config = config_service or ConfigService()	# ⚙️ Джерело налаштувань

        cfg_bold = self._get_cfg_list("image_generation.font_paths.bold")	# 🧾 Конфіг для bold
        cfg_mono = self._get_cfg_list("image_generation.font_paths.mono")	# 🧾 Конфіг для mono

        self._bold_search = self._chain_paths(
            [FONTS_DIR / "Roboto-Bold.ttf"],	# 📦 Вбудований asset
            [Path(path) for path in cfg_bold],	# ⚙️ Конфігурований список
            [Path(path) for path in DEFAULT_BOLD_PATHS],	# 🖥️ Системні дефолти
        )	# 📚 Фінальний список шляхів bold
        self._mono_search = self._chain_paths(
            [FONTS_DIR / "RobotoMono-Regular.ttf"],
            [Path(path) for path in cfg_mono],
            [Path(path) for path in DEFAULT_MONO_PATHS],
        )	# 📚 Фінальний список шляхів mono

        self._dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))	# 🖌️ «Полотно» для вимірів

        self._log_missing_asset(FONTS_DIR / "Roboto-Bold.ttf")	# ℹ️ Нагадуємо про відсутні файли
        self._log_missing_asset(FONTS_DIR / "RobotoMono-Regular.ttf")

        self._cache: dict[tuple[FontType, int], FontLike] = {}	# ♻️ Кеш шрифтів
        logger.debug("🔤 FontService ініціалізовано (bold=%d, mono=%d).", len(self._bold_search), len(self._mono_search))

    # ================================
    # 📣 ПУБЛІЧНЕ API
    # ================================
    def get_font(self, font_type: FontType, size: int) -> FontLike:
        """🔤 Повертає шрифт обраного типу/розміру з кешем та fallback-ами."""
        key = (font_type, size)	# 🔑 Ключ кешу
        cached = self._cache.get(key)	# ♻️ Спроба кешу
        if cached is not None:
            logger.debug("♻️ Font cache hit (%s %s pt).", font_type.value, size)
            return cached

        candidates = self._bold_search if font_type is FontType.BOLD else self._mono_search	# 📚 Список пошуку
        for path in candidates:	# 🔁 Перебираємо шляхи
            try:
                if path.exists():	# ✅ Файл доступний
                    font = ImageFont.truetype(str(path), size)	# 🆕 Завантажуємо шрифт
                    self._cache[key] = font	# ♻️ Кладемо у кеш
                    logger.info("✅ Шрифт %s (%s pt) завантажено з %s", font_type.value, size, path)
                    return font
            except OSError as exc:	# ⚠️ Файл може бути пошкоджений
                logger.debug("⚠️ Неможливо прочитати шрифт %s: %s", path, exc)
                continue

        logger.warning("⚠️ Шрифт '%s' не знайдено, використовую стандартний.", font_type.value)
        fallback = ImageFont.load_default()	# 🪢 Pillow fallback
        self._cache[key] = fallback
        return fallback

    def get_text_width(self, text: str, font: FontLike) -> int:
        """📏 Обчислює ширину тексту у пікселях для переданого шрифту."""
        if not text:	# 🪣 Порожній рядок
            return 0
        try:
            width = int(self._dummy_draw.textlength(str(text), font=font))	# 📏 Основний спосіб
            logger.debug("📏 Text width '%s' = %s px.", text, width)
            return width
        except Exception as exc:	# ⚠️ Pillow версія без textlength
            logger.debug("⚠️ textlength не спрацював, fallback textbbox: %s", exc)
            bbox = self._dummy_draw.textbbox((0, 0), str(text), font=font)	# 🔁 Fallback
            return int((bbox[2] - bbox[0]) if bbox else 0)

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    def _get_cfg_list(self, key: str) -> List[str]:
        """🧾 Повертає списки шляхів із конфіга; ігнорує не-рядки."""
        raw_value = self._config.get(key, [])	# 🧾 Значення з конфіга
        if not isinstance(raw_value, (list, tuple)):
            logger.debug("ℹ️ Ключ %s не є списком у конфігу.", key)
            return []
        normalized: List[str] = []	# 📦 Результуючий список
        for item in raw_value:	# 🔁 Перетворюємо елементи на рядки
            try:
                path_str = str(item).strip()	# 🧼 Очищаємо значення
                if path_str:
                    normalized.append(path_str)
            except Exception as exc:
                logger.debug("⚠️ Неможливо використати шлях '%s': %s", item, exc)
        return normalized

    @staticmethod
    def _chain_paths(*groups: Iterable[Path]) -> List[Path]:
        """🔗 Обʼєднує групи шляхів у один список без дублів."""
        flattened: List[Path] = []	# 📦 Плоский список
        for group in groups:
            flattened.extend(list(group))
        seen: set[Path] = set()	# ♻️ Контроль дублів
        unique: List[Path] = []	# 📦 Унікальні шляхи
        for path in flattened:
            if path not in seen:
                unique.append(path)
                seen.add(path)
        return unique

    @staticmethod
    def _log_missing_asset(path: Path) -> None:
        """ℹ️ Повідомляє про відсутність вбудованого шрифту (не фатально)."""
        if not path.exists():
            logger.info("ℹ️ Вкладений шрифт відсутній: %s (буде використано fallback)", path)


__all__ = ["FontService"]
