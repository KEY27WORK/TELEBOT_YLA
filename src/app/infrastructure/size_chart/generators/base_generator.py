# 📐 src/app/infrastructure/size_chart/generators/base_generator.py
"""
📐 BaseTableGenerator — абстрактний клас генераторів PNG таблиць розмірів.

🔹 Працює з параметризованою канвою (розміри, відступи, кольори).
🔹 Гарантує безпечне приведення даних до `Dict[str, List[str>]`.
🔹 Надає утиліти для вимірювання тексту та його центрованого розміщення.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from PIL import Image, ImageDraw											# 🎨 Побудова канви та тексту

# 🔠 Системні імпорти
import logging																# 🧾 Детальне логування генератора
from abc import ABC, abstractmethod										# 🏛️ Абстрактний базовий клас
from typing import Dict, List, Mapping, Optional, Sequence, Tuple			# 🧰 Типові колекції

# 🧩 Внутрішні модулі проєкту
from app.domain.image_generation.interfaces import FontLike				# 🔤 Інтерфейс шрифтів
from app.infrastructure.image_generation.font_service import FontService	# 🧵 Сервіс роботи зі шрифтами
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базовий префікс логів

logger = logging.getLogger(f"{LOG_NAME}.infrastructure.size_chart.base_generator")	# 🧾 Локальний логер

# ================================
# 🧱 БАЗОВИЙ КЛАС ГЕНЕРАТОРА
# ================================
class BaseTableGenerator(ABC):
    """
    🧱 Базує загальний функціонал побудови таблиць розмірів.
    """

    IMG_WIDTH = 1080														# 📐 Ширина канви
    IMG_HEIGHT = 1920														# 📐 Висота канви
    PADDING = 20															# 🔲 Відступи від країв

    def __init__(self, size_chart: Dict[str, List], output_path: str, font_service: FontService) -> None:
        """
        ⚙️ Ініціалізує базові параметри таблиці.

        Args:
            size_chart (Dict[str, List]): 📊 Дані таблиці розмірів.
            output_path (str): 💾 Шлях для збереження результуючого PNG.
            font_service (FontService): 🔤 Сервіс шрифтів для викликів Pillow.
        """
        self.size_chart = size_chart.copy()									# 🧩 Копіюємо дані, щоб не мутувати оригінал
        logger.debug(
            "🧱 BaseTableGenerator init (output=%s, raw_keys=%s)",
            output_path,
            list(self.size_chart.keys()),
        )
        self.output_path = output_path										# 💾 Де зберегти готову таблицю
        self.font_service = font_service										# 🔤 Доступ до шрифтів

        self._background_color: str = "white"								# 🎨 Колір тла за замовчуванням
        self._text_color: str = "black"										# 🖋️ Основний колір тексту

        raw_title = self.size_chart.pop("Title", "Таблиця розмірів")			# 🏷️ Витягаємо заголовок таблиці
        if isinstance(raw_title, (list, tuple)) and raw_title:
            self.title: str = str(raw_title[0])								# 🏷️ Беремо перший елемент списку
        else:
            self.title = str(raw_title)										# 🏷️ Переводимо в рядок будь-яке значення
        logger.debug("🏷️ Заголовок таблиці: %s", self.title)

        headers_raw = self.size_chart.pop("Розмір", self.size_chart.pop("Размер", []))	# 📌 Заголовки колонок
        if isinstance(headers_raw, (list, tuple)):
            self.headers: List[str] = [str(value) for value in headers_raw]	# 📌 Нормалізуємо список
        elif headers_raw:
            self.headers = [str(headers_raw)]									# 📌 Один рядок → список з одним елементом
        else:
            self.headers = []													# 📌 За замовчуванням — порожній список
        logger.debug("📌 Заголовки колонок (%d): %s", len(self.headers), self.headers)

        self.parameters_map: Dict[str, List[str]] = self._build_parameters_map(self.size_chart)	# 🗃️ Безпечні параметри
        logger.debug("🗂️ Параметри таблиці нормалізовано (%d ключів).", len(self.parameters_map))

        self.image = Image.new("RGB", (self.IMG_WIDTH, self.IMG_HEIGHT), self._background_color)	# 🖼️ Канва зображення
        self.draw = ImageDraw.Draw(self.image)								# ✏️ Інструмент для малювання
        logger.debug(
            "🖼️ Канва створена (%dx%d, bg=%s).",
            self.IMG_WIDTH,
            self.IMG_HEIGHT,
            self._background_color,
        )

    @staticmethod
    def _build_parameters_map(raw: Mapping[str, object]) -> Dict[str, List[str]]:
        """
        🧹 Перетворює входні дані у безпечний словник `Dict[str, List[str>]`.

        Args:
            raw (Mapping[str, object]): Вихідні дані таблиці (можуть містити різні типи).

        Returns:
            Dict[str, List[str]]: Словник з рядковими ключами та значеннями-списками рядків.
        """
        clean_map: Dict[str, List[str]] = {}
        logger.debug("🧹 Починаємо нормалізацію %d параметрів.", len(raw))
        for key, value in raw.items():
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):			# 🧪 Відкидаємо строки/байти
                clean_map[key] = [str(item) for item in value]								# 🧾 Приводимо кожен елемент до str
                logger.debug("🧾 Параметр '%s' → %d значень.", key, len(clean_map[key]))
            else:
                logger.debug("⏭️ Параметр '%s' пропущено (type=%s).", key, type(value).__name__)
        logger.debug("🧹 Нормалізацію завершено: %d валідних параметрів.", len(clean_map))
        return clean_map

    def _get_values(self, param: str) -> List[str]:
        """
        📄 Повертає список значень параметра або порожній список.

        Args:
            param (str): Назва параметра.

        Returns:
            List[str]: Значення, якщо знайдені, або порожній список.
        """
        values = self.parameters_map.get(param, [])											# 🔁 Повертаємо копію списку значень
        logger.debug("📄 _get_values('%s') -> %d елементів.", param, len(values))
        return values

    def _text_size(self, text: str, font: FontLike) -> Tuple[int, int]:
        """
        📏 Обчислює ширину та висоту тексту з урахуванням шрифту.

        Args:
            text (str): Текст, який потрібно виміряти.
            font (FontLike): Шрифт із сервісу `FontService`.

        Returns:
            Tuple[int, int]: Кортеж (width, height) у пікселях.
        """
        normalized = "" if text is None else str(text)										# 🧼 Захищаємося від None
        logger.debug(
            "📏 Вимірювання тексту '%s' (font_size=%s).",
            normalized,
            getattr(font, "size", "unknown"),
        )
        try:
            bbox = self.draw.textbbox((0, 0), normalized, font=font)						# 📦 Намагаємося отримати точний bbox
            width = int(bbox[2] - bbox[0])
            height = int(bbox[3] - bbox[1])
            logger.debug("📐 textbbox: width=%d, height=%d.", width, height)
            return width, height															# 📐 Обчислюємо ширину/висоту
        except Exception:
            try:
                width = int(self.draw.textlength(normalized, font=font))					# 📏 Резервний підрахунок ширини
                logger.debug("📏 textlength fallback width=%d.", width)
            except Exception:
                width = len(normalized) * max(getattr(font, "size", 16) // 2, 6)			# 📏 Оціночний fallback
                logger.debug("📏 Fallback width через довжину рядка=%d.", width)
            try:
                getmetrics = getattr(font, "getmetrics", None)                            # 📈 Безпечний доступ до метрики шрифту
                if callable(getmetrics):
                    metrics = getmetrics()
                    # metrics may be a tuple/list (ascent, descent), an object with attributes,
                    # or a single numeric value — handle all safely
                    if isinstance(metrics, (tuple, list)) and len(metrics) >= 2:
                        ascent, descent = int(metrics[0]), int(metrics[1])
                    elif hasattr(metrics, "ascent") or hasattr(metrics, "descent"):
                        ascent = int(getattr(metrics, "ascent", 0))
                        descent = int(getattr(metrics, "descent", 0))
                    elif isinstance(metrics, (int, float)):
                        ascent = int(metrics)
                        descent = 0
                    else:
                        ascent = getattr(font, "size", 16)
                        descent = 0
                    height = ascent + descent
                else:
                    height = getattr(font, "size", 16)                                   # 📈 fallback на розмір шрифту
            except Exception:
                height = getattr(font, "size", 16)                                         # 📈 fallback на розмір шрифту
            logger.debug("📏 Fallback height=%d.", height)
            return int(width), int(height)

    def draw_text_centered(
        self,
        text: str,
        x_center: int,
        y_center: int,
        font: FontLike,
        fill: Optional[str] = None,
    ) -> None:
        """
        🎯 Малює текст горизонтально та вертикально по центру.

        Args:
            text (str): Рядок, який виводиться.
            x_center (int): Центр по осі X.
            y_center (int): Центр по осі Y.
            font (FontLike): Шрифт для відображення.
            fill (str | None): Колір тексту (якщо None — використовується дефолтний).
        """
        fill_color = fill or self._text_color											# 🎨 Використовуємо переданий колір або дефолтний
        width, height = self._text_size(text, font)										# 📐 Обчислюємо габарити тексту
        logger.debug(
            "🎯 Малюємо '%s' по центру (%d, %d) → box %dx%d, fill=%s.",
            text,
            x_center,
            y_center,
            width,
            height,
            fill_color,
        )
        self.draw.text(
            (int(x_center - width // 2), int(y_center - height // 2)),
            str(text),																	# 📝 Переконуємося, що текст — рядок
            font=font,
            fill=fill_color,
        )

    def save_png(self) -> str:
        """
        💾 Зберігає сформоване зображення у форматі PNG та повертає шлях.

        Returns:
            str: Шлях до збереженого файлу.
        """
        logger.info("💾 Зберігаємо PNG таблиці розмірів у %s", self.output_path)
        self.image.save(self.output_path, "PNG")										# 💾 Зберігаємо канву
        logger.debug("💾 PNG успішно записано (%s).", self.output_path)
        return self.output_path															# 🔁 Повертаємо шлях

    # ================================
    # 🔌 ІНТЕРФЕЙС НАЩАДКІВ
    # ================================
    @abstractmethod
    async def generate(self) -> str:
        """
        🛠️ Реалізує повний сценарій відрисовки таблиці та збереження PNG.

        Returns:
            str: Шлях до згенерованого файлу.
        """
        raise NotImplementedError("Метод generate() має бути реалізований у підкласі.")
