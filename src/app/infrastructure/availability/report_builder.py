# 📄 app/infrastructure/availability/report_builder.py
"""
📄 Генерує форматовані звіти про наявність товарів у регіонах.

🔹 Приймає доменні DTO (`RegionStock`, `AvailabilityReport`) із сирими даними.  
🔹 Формує «легенду» по регіонах (✅/❌/❔) і тексти для публічного та адмінського каналів.  
🔹 Повертає `AvailabilityReports` із готовими рядками для Telegram.
"""

from __future__ import annotations

# 🔠 Системні імпорти
import logging                                                      # 🧾 Логування побудови звітів
from typing import Iterable, List                                   # 📐 Типи публічного API

# 🧩 Внутрішні модулі проєкту
from app.domain.availability.interfaces import AvailabilityReport, RegionStock  # 📦 DTO домену
from app.domain.availability.status import AvailabilityStatus                  # 🧭 Статуси наявності
from app.infrastructure.availability.dto import AvailabilityReports            # 📦 DTO результатів
from app.infrastructure.availability.formatter import ColorSizeFormatter       # 🎨 Форматер тексту
from app.shared.utils.logger import LOG_NAME                                   # 🏷️ Назва логера

logger = logging.getLogger(LOG_NAME)                                           # 🧾 Модульний логер


# ================================
# ♻️ ХЕЛПЕР ДЛЯ ЛЕГЕНДИ
# ================================
def _region_symbol(statuses: Iterable[AvailabilityStatus]) -> str:
    """Визначає символ регіону залежно від наявності."""
    has_no = False                                                   # ❌ Чи бачили NO
    for status in statuses:
        if status is AvailabilityStatus.YES:
            return "✅"                                             # ✅ Є хоч один YES
        if status is AvailabilityStatus.NO:
            has_no = True                                            # ⚠️ Прапорець NO
    return "❌" if has_no else "❔"                                 # ❔ Якщо лише UNKNOWN або порожньо


# ================================
# 🏛️ СЕРВІС ПОБУДОВИ ЗВІТІВ
# ================================
class AvailabilityReportBuilder:
    """🏛️ Генерує публічний і адмінський звіти з даних про наявність."""

    def __init__(self, formatter: ColorSizeFormatter) -> None:
        self._formatter = formatter                                  # 🎨 Форматер для різних каналів
        logger.debug("⚙️ AvailabilityReportBuilder init (%s)", formatter)

    def build(
        self,
        region_results: List[RegionStock],
        report_dto: AvailabilityReport,
    ) -> AvailabilityReports:
        """📦 Будує DTO `AvailabilityReports` на основі доменних даних."""
        logger.info("🧾 Побудова звіту про наявність: регіонів=%d", len(region_results or []))

        region_results = region_results or []                        # 🛡️ Захист від None

        region_lines: List[str] = []                                 # 🧾 Легенда (flag + символ)
        for region_data in region_results:
            statuses_iter = (
                status
                for sizes in (region_data.stock_data or {}).values()
                for status in (sizes or {}).values()
            )                                                         # ♻️ Плоска ітерація по статусах
            symbol = _region_symbol(statuses_iter)
            flag = self._formatter.get_flag(region_data.region_code)
            region_lines.append(f"{flag} - {symbol}")
            logger.debug("🏳️ %s → %s", region_data.region_code, symbol)

        region_lines.append(f"{self._formatter.get_flag('ua')} - ❌")  # 📏 Бізнес-правило: 'ua' завжди ❌
        region_checks = "\n".join(region_lines) if region_lines else f"{self._formatter.get_flag('ua')} - ❌"

        public_format = self._formatter.format_public_report(report_dto.merged_stock)
        admin_format = self._formatter.format_admin_report(
            availability=report_dto.availability_by_region,
            all_sizes_map=report_dto.all_sizes_map,
        )                                                             # 📊 Тексти для різних каналів
        logger.debug("📝 Публічний текст довжиною %d символів.", len(public_format))

        public_text_header = "🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ"
        admin_text_header = "👨‍🎓 Детально по регіонах"

        reports = AvailabilityReports(
            public_report=f"{region_checks}\n\n{public_text_header}:\n{public_format}",
            admin_report=f"{admin_text_header}:\n{admin_format}",
        )                                                             # 📦 Обгортаємо у DTO
        logger.info("✅ Звіти побудовано (public+admin).")
        return reports
