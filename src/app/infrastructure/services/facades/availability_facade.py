# 📦 app/infrastructure/services/facades/availability_facade.py
"""
📦 `AvailabilityFacade` — тонка обгортка над AvailabilityProcessingService.

🔹 Ізолює форматування заголовків і тексту наявності від решти коду.  
🔹 Спрощує мокування та підміну у тестах `ProductProcessingService`.  
🔹 Працює за принципом best-effort: якщо звіт некоректний, повертає порожні значення.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging															# 🧾 Логування фасаду
from dataclasses import dataclass											# 🧱 DTO результату
from typing import Any, Iterable, Optional, cast							# 🧰 Типи для обробки звітів

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.availability.availability_processing_service import (	# ✅ Сервіс наявності
    AvailabilityProcessingService,
)
from app.shared.utils.logger import LOG_NAME								# 🏷️ Базове імʼя логера

logger = logging.getLogger(LOG_NAME)										# 🧾 Логер фасаду


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    """📦 DTO з готовим заголовком та текстом кольорів/розмірів."""

    header: str															# 🏷️ Заголовок (назва товару + лінк)
    colors_text: str														# 🎨 Текстовий блок з кольорами/розмірами


class AvailabilityFacade:
    """
    🧩 Обгортка над `AvailabilityProcessingService`.

    Використовується, щоб:
      • приховати деталі форматування звітів;
      • спростити заміну залежностей у тестах;
      • забезпечити стабільний контракт: `build(url) -> AvailabilityResult`.
    """

    def __init__(self, processing_service: AvailabilityProcessingService) -> None:
        self._svc = processing_service										# 🔗 Зберігаємо сервіс наявності
        logger.debug("📦 AvailabilityFacade ініціалізовано.")

    async def build(self, url: str) -> AvailabilityResult:
        """
        🔗 Формує заголовок і текст кольорів/розмірів для товару.

        Args:
            url (str): URL товару.

        Returns:
            AvailabilityResult: DTO з двома рядками для UI.
        """
        logger.info("📦 Побудова звіту наявності для %s", url)
        processed = await self._svc.process(url)							# 📤 Викликаємо сервіс наявності
        if not processed:													# 🚫 Немає даних — повертаємо порожні поля
            logger.warning("⚠️ AvailabilityProcessingService повернув порожній результат для %s", url)
            return AvailabilityResult(header="", colors_text="")

        header = self._format_header(processed)								# 🏷️ Побудова заголовка
        colors_text = self._format_colors(processed)							# 🎨 Побудова тексту кольорів/розмірів
        logger.debug("📦 Звіт готовий: header_len=%d colors_len=%d", len(header), len(colors_text))
        return AvailabilityResult(header=header, colors_text=colors_text)

    # ================================
    # 🧱 ВСПОМОЖНІ ФОРМАТЕРИ
    # ================================
    def _format_header(self, processed: Any) -> str:
        """🏷️ Формує заголовок із DTO, не залежачи від конкретних полів."""

        header_dto = getattr(processed, "header", None)						# 🧾 Заголовок із DTO
        title = (
            getattr(header_dto, "title", None)
            or getattr(header_dto, "name", None)
            or getattr(header_dto, "text", None)
            or getattr(header_dto, "label", None)
            or str(header_dto or "")
        )																	# 🏷️ Витягуємо найбільш релевантну назву
        link = getattr(header_dto, "url", None) or getattr(header_dto, "product_url", None)  # 🔗 Пошук URL
        result = f"{title} — {link}" if link else title						# 🧵 Об'єднуємо назву та посилання
        logger.debug("🏷️ Заголовок availability: %s", result)
        return result						# 🧵 Об'єднуємо назву та посилання

    def _format_colors(self, processed: Any) -> str:
        """🎨 Формує блок з кольорами/розмірами, враховуючи різні форми DTO."""

        reports = getattr(processed, "reports", None)						# 📊 Звіти про наявність
        if reports is None:
            logger.debug("🎨 Звіти відсутні — colors_text порожній.")
            return ""														# 🚫 Немає інформації — повертаємо порожній текст

        to_text = getattr(reports, "to_text", None)
        if callable(to_text):												# 🧠 DTO вже вміє формувати текст
            try:
                text = str(to_text())										# 📜 Користуємося готовим методом
                logger.debug("🎨 Використано reports.to_text() (%d символів).", len(text))
                return text
            except Exception:
                pass														# 🤫 Переходимо до ручної обробки

        if isinstance(reports, (str, bytes)):								# 🎯 DTO повернув рядок — просто кастуємо
            text = str(reports)
            logger.debug("🎨 reports — рядок (%d символів).", len(text))
            return text

        # 🧪 Далі — ручні фолбеки для різних структур
        sequence = self._as_iterable(reports)								# 🔄 Пробуємо отримати ітерований вигляд
        if sequence is None:
            return str(reports)												# ❗ Не вдалося — повертаємо str()

        try:
            items = list(cast(Iterable[Any], sequence))						# 📋 Матеріалізуємо ітератор
        except Exception:
            return str(reports)												# ❗ Несподіваний збій — повертаємо str()

        if not items:
            logger.debug("🎨 reports iterable, але список порожній.")
            return ""														# 💤 Порожній список — повертаємо порожній текст
        if isinstance(items[0], tuple) and len(items[0]) == 2:				# 📦 Схоже на dict.items()
            text = "\n".join(f"{key}: {value}" for key, value in items)		# 🧾 Форматуємо як ключ: значення
            logger.debug("🎨 reports формат dict.items() (%d рядків).", len(items))
            return text
        text = "\n".join(str(item) for item in items)						# 📋 Інші випадки — просто join()
        logger.debug("🎨 reports перетворено у список (%d рядків).", len(items))
        return text

    def _as_iterable(self, reports: Any) -> Optional[Iterable[Any]]:
        """
        🔄 Повертає ітерований вигляд звітів, пробуючи популярні протоколи `to_list`, `items`, `__iter__`.

        Args:
            reports (Any): Об'єкт зі звітом.

        Returns:
            Iterable[Any] | None: Ітерована форма або None, якщо не вдалося.
        """
        to_list = getattr(reports, "to_list", None)
        if callable(to_list):												# 🧰 DTO має зручний метод
            try:
                candidate = to_list()
                return candidate if isinstance(candidate, Iterable) else None
            except Exception:
                return None

        items = getattr(reports, "items", None)
        if callable(items):													# 🧰 Словник або dict-like об'єкт
            try:
                candidate = items()
                return candidate if isinstance(candidate, Iterable) else None
            except Exception:
                return None
        if isinstance(items, Iterable):
            return items													# 🧰 Може бути готовий ітерований атрибут

        if hasattr(reports, "__iter__"):									# 🔁 Підтримує ітерацію напряму
            return reports

        if hasattr(reports, "__len__") and hasattr(reports, "__getitem__"):	# 📐 Sequence protocol (len + getitem)
            try:
                return (reports[index] for index in range(len(reports)))	# type: ignore[arg-type]
            except Exception:
                return None

        fallback = getattr(reports, "reports", None) or getattr(reports, "data", None)  # 📦 Пошук вкладених структур
        return fallback if isinstance(fallback, Iterable) else None			# 🔁 Повертаємо, якщо це Iterable
