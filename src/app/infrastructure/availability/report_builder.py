# 📄 app/infrastructure/availability/report_builder.py
"""
📄 report_builder.py — Генератор форматованих звітів про наявність товару.

🔹 Клас `AvailabilityReportBuilder`:
- Створює текстові звіти для Telegram на основі даних із доменного шару.
- Повертає результат у вигляді структурованого DTO.
"""

# 🔠 Системні імпорти
import logging												# 🧾 Логування
from typing import List										# 🧰 Типізація списку

# 🧩 Внутрішні модулі проєкту
from .formatter import ColorSizeFormatter							# 🎨 Форматування кольорів і розмірів
from app.domain.availability.services import AvailabilityReport, RegionStock	# 📦 DTO з доменного шару
from .dto import AvailabilityReports								# 📦 DTO для відповідей у Telegram
from app.shared.utils.logger import LOG_NAME							# 🧾 Імʼя логгера

logger = logging.getLogger(LOG_NAME)


# ================================
# 📄 КЛАС-ГЕНЕРАТОР ЗВІТІВ
# ================================
class AvailabilityReportBuilder:
    """
    📊 Генератор звітів, що працює з чистими DTO (`AvailabilityReport`, `RegionStock`).

    ✅ Призначення:
    - Приймає сирі дані по регіонах (`RegionStock`).
    - Формує два текстові звіти: публічний та адмінський.
    - Повертає результат у вигляді DTO `AvailabilityReports`.
    """

    def __init__(self, formatter: ColorSizeFormatter):
        """
        🔧 Ініціалізація генератора через DI форматера.

        Args:
            formatter (ColorSizeFormatter): 🎨 Сервіс для форматування виводу.
        """
        self.formatter = formatter										# 🎨 Зберігаємо форматер як залежність

    # ================================
    # 🛠 ГОЛОВНИЙ МЕТОД
    # ================================
    def build(
        self,
        region_results: List[RegionStock],
        report_dto: AvailabilityReport
    ) -> AvailabilityReports:
        """
        🛠 Формує звіти, використовуючи дані з доменного шару, і повертає їх у DTO.

        Args:
            region_results (List[RegionStock]): 📊 Результати наявності по регіонах.
            report_dto (AvailabilityReport): 📦 Зведений звіт з availability та розмірами.

        Returns:
            AvailabilityReports: 📄 DTO з текстовими звітами.
        """

        # ================================
        # 📍 Побудова прапорців регіонів
        # ================================
        region_lines = []
        for region_data in region_results:
            is_available = any(
                available
                for sizes in region_data.stock_data.values()
                for available in sizes.values()
            )
            region_lines.append(
                f"{self.formatter.get_flag(region_data.region_code)} - {'✅' if is_available else '❌'}"
            )

        region_lines.append(f"{self.formatter.get_flag('ua')} - ❌")					# 🇺🇦 Для локального регіону завжди ❌
        region_checks = "\n".join(region_lines)								# 🔗 Об'єднання у текстовий блок

        # ================================
        # 🧾 Формування текстів звітів
        # ================================
        public_format = self.formatter.format_public_report(report_dto.merged_stock)		# 📢 Публічний формат (без деталей)
        admin_format = self.formatter.format_admin_report(
            availability=report_dto.availability_by_region,
            all_sizes_map=report_dto.all_sizes_map
        )															# 🧠 Адмінський формат зі всіма деталями

        logger.info("📝 Згенеровано звіти про наявність.")

        # ================================
        # 📦 Побудова DTO для Telegram
        # ================================
        return AvailabilityReports(
            public_report=f"{region_checks}\n\n🎨 ДОСТУПНІ КОЛЬОРИ ТА РОЗМІРИ:\n{public_format}",	# ✅ Основний текст для користувача
            admin_report=f"👨‍🎓 Детально по регіонах:\n{admin_format}" 				# 🔍 Технічна інформація для адміна
        )