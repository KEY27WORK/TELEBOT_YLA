# 🧭 src/app/infrastructure/size_chart/size_chart_service.py
from __future__ import annotations

# 🌐 Зовнішні бібліотеки
try:
    from prometheus_client import Counter									# 📈 Метрики Prometheus
except Exception:															# pragma: no cover
    Counter = None															# 🚫 Фолбек, якщо Prometheus недоступний

# 🔠 Системні імпорти
import asyncio																# ⏳ Асинхронні операції
import logging																# 🧾 Логування пайплайна
import os																	# 🌍 Робота з env-змінними
import time																	# ⌛ Вимірювання тривалості
import uuid																	# 🆔 UUIDv5 для task_id
from collections import deque												# 📚 Буфер для автотюнингу
from dataclasses import dataclass, field									# 🧱 DTO прогресу
from enum import Enum														# 🏷️ Перелік стадій
from pathlib import Path													# 📁 Тимчасові директорії
from typing import (														# 🧰 Типізація API
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

# 🧩 Внутрішні модулі проєкту
from app.config.config_service import ConfigService						# ⚙️ Конфігурація сервісу
from app.domain.size_chart.interfaces import (								# 🧠 Контракти домену
    ISizeChartFinder,
    ISizeChartService,
    ProgressFn,
)
from app.infrastructure.size_chart.dto import (							# 📋 DTO результатів OCR
    SizeChartOcrResult,
    SizeChartOcrStatus,
)
from app.infrastructure.size_chart.general import (						# 🌐 Робота з універсальними таблицями
    GeneralChartCache,
    GeneralChartVariant,
    ProductGender,
    YoungLAProductGenderDetector,
)
from app.infrastructure.size_chart.image_downloader import (				# ⬇️ Завантаження зображень
    DownloadError,															# noqa: F401
    DownloadOutcome,
    DownloadResult,
    ImageDownloader,
)
from app.infrastructure.size_chart.ocr_service import OCRService			# 🔤 OCR сервіс
from app.infrastructure.size_chart.table_generator_factory import (		# 🖼️ Фабрика генераторів таблиць
    TableGeneratorFactory,
)
from app.shared.utils.logger import LOG_NAME								# 🏷️ Ім'я логера
from app.shared.utils.prompt_service import ChartType as PromptChartType	# 🧠 Типи промтів для OCR
from app.shared.utils.prompts import ChartType								# 🧾 Публічні типи таблиць

_GENERAL_MEN_PATTERNS: Tuple[str, ...] = (
    "size_chart_top_jogger",
    "mens-size-chart",
    "men-size-chart",
)
_GENERAL_WOMEN_PATTERNS: Tuple[str, ...] = (
    "ylafh-size-chart",
    "women-size-chart",
    "womens-size-chart",
)


# ================================
# 🧾 ЛОГЕР ТА МЕТРИКИ
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai")								# 🧾 Логер пайплайна size-chart

if Counter:																# 📈 Метрики доступні — реєструємо лічильники
    SIZECHART_DOWNLOAD_ERRORS_TOTAL = Counter(								# 📉 Помилки завантаження
        "sizechart_download_errors_total",
        "Помилки завантаження таблиць розмірів (оркестрація) за причинами",
        ["reason"],
    )
    SIZECHART_OCR_ERRORS_TOTAL = Counter(									# 📉 Помилки OCR
        "sizechart_ocr_errors_total",
        "Помилки OCR під час розпізнавання таблиць розмірів",
        ["status"],
    )
    SIZECHART_GENERATE_ERRORS_TOTAL = Counter(								# 📉 Помилки генерації PNG
        "sizechart_generate_errors_total",
        "Помилки генерації PNG таблиць розмірів",
        ["kind"],
    )
    SIZECHART_CANCELLED_TOTAL = Counter(									# 🧮 Лічильник скасувань (IMP-020)
        "sizechart_cancelled_total",
        "Кількість скасованих пайплайнів size-chart",
    )
else:																		# 🪃 Граційний фолбек без Prometheus
    SIZECHART_DOWNLOAD_ERRORS_TOTAL = None									# type: ignore
    SIZECHART_OCR_ERRORS_TOTAL = None										# type: ignore
    SIZECHART_GENERATE_ERRORS_TOTAL = None									# type: ignore
    SIZECHART_CANCELLED_TOTAL = None										# type: ignore


def _inc_dl_err(reason: str) -> None:
    """
    🧮 Збільшує метрику помилок завантаження, ігнорує винятки.

    Args:
        reason (str): Код або опис причини.
    """
    if SIZECHART_DOWNLOAD_ERRORS_TOTAL:									# 🧾 Лічильник активний
        try:
            SIZECHART_DOWNLOAD_ERRORS_TOTAL.labels(reason=reason).inc()	# 🔢 Оновлюємо лічильник
        except Exception:
            pass															# 🤫 Ігноруємо збій метрики


def _inc_ocr_err(status: str) -> None:
    """
    🧮 Збільшує метрику помилок OCR.

    Args:
        status (str): Статус помилки, отриманий від OCR.
    """
    if SIZECHART_OCR_ERRORS_TOTAL:										# 🧾 Лічильник активний
        try:
            SIZECHART_OCR_ERRORS_TOTAL.labels(status=status).inc()			# 🔢 Фіксуємо невдалий OCR
        except Exception:
            pass															# 🤫 Не валимо пайплайн


def _inc_gen_err(kind: str) -> None:
    """
    🧮 Збільшує метрику помилок генерації PNG.

    Args:
        kind (str): Категорія помилки («factory_error», «generate_error»).
    """
    if SIZECHART_GENERATE_ERRORS_TOTAL:									# 🧾 Лічильник активний
        try:
            SIZECHART_GENERATE_ERRORS_TOTAL.labels(kind=kind).inc()			# 🔢 Лічимо збої генерації
        except Exception:
            pass															# 🤫 Утримуємо сервіс від падіння


def _inc_cancelled() -> None:
    """
    🧮 Збільшує метрику скасованих пайплайнів.
    """
    if SIZECHART_CANCELLED_TOTAL:										# 🧾 Лічильник активний
        try:
            SIZECHART_CANCELLED_TOTAL.inc()								# 🔢 Фіксуємо факт скасування
        except Exception:
            pass															# 🤫 Ігноруємо помилку метрики


# ================================
# 🧭 СТАДІЇ ПРОГРЕСУ
# ================================
class Stage(Enum):
    """📍 Етапи життєвого циклу завдання size-chart."""

    START = "start"
    DOWNLOAD_START = "download_start"
    DOWNLOAD_OK = "download_ok"
    DOWNLOAD_FAIL = "download_fail"
    OCR_START = "ocr_start"
    OCR_OK = "ocr_ok"
    OCR_FAIL = "ocr_fail"
    GENERATE_START = "generate_start"
    GENERATE_OK = "generate_ok"
    GENERATE_FAIL = "generate_fail"
    DONE = "done"


# ================================
# 🧾 Варіанти універсальних таблиць
# ================================
# ================================
# 📦 DTO ПРОГРЕСУ
# ================================
@dataclass
class SizeChartProgress:
    """
    📦 Опис повідомлення прогресу для зовнішніх споживачів.

    Attributes:
        idx (int): Індекс задачі в черзі.
        url (str): Початковий URL зображення.
        chart_type (ChartType): Тип таблиці розмірів.
        stage (Stage): Поточна стадія.
        started_at (float): Позначка часу старту задачі.
        elapsed (float): Скільки триває обробка (секунди).
        path (str | None): Шлях до результату (PNG) чи завантаженого файлу.
        error (str | None): Текст помилки, якщо стався збій.
        bytes_downloaded (int | None): Скільки байтів отримано під час завантаження.
        sha256 (str | None): Хеш файлу, якщо був обчислений.
        task_id (str): Стабільний ідентифікатор задачі.
        extra (dict[str, Any]): Додаткова інформація (для сумісності).
    """

    idx: int																# 🔢 Порядковий номер задачі
    url: str																# 🌐 Джерельне посилання
    chart_type: ChartType													# 🧾 Тип таблиці
    stage: Stage															# 🧭 Поточний етап
    started_at: float														# ⏱️ Час старту
    elapsed: float															# 🕒 Пройдений час (секунди)
    path: Optional[str] = None												# 📁 Шлях до файлу
    error: Optional[str] = None											# ❌ Опис помилки
    bytes_downloaded: Optional[int] = None									# 📦 Розмір завантажених даних
    sha256: Optional[str] = None											# 🔐 Контрольний хеш
    task_id: str = ""														# 🆔 Стабільний UUID задачі
    extra: dict[str, Any] = field(default_factory=dict)					# 🧰 Додаткові атрибути


ProgressCallback = Callable[[SizeChartProgress], Optional[Awaitable[None]]]	# 🔔 Тип публічного колбека


# ================================
# 🏛️ СЕРВІС ОРКЕСТРАЦІЇ
# ================================
class SizeChartService(ISizeChartService):
    """
    🏛️ Координує пайплайн «пошук → завантаження → OCR → генерація PNG».

    Підтримує коректне скасування (IMP-020) та унікальні `task_id` (IMP-046).
    """

    _TMP_DIR_NAME = os.getenv("SIZE_CHART_TMP", "temp_size_charts")			# 📁 Тимчасовий каталог
    _GENERAL_CACHE_DIR = os.getenv("SIZE_CHART_GENERAL_CACHE", "var/general_size_charts")	# 💾 Кеш універсальних таблиць
    _LEGACY_MAX_CONCURRENCY = int(os.getenv("SIZE_CHART_CONCURRENCY", "0") or "0")	# 🪢 Історичне обмеження

    _NS_SHA = uuid.UUID("b8a7d2c6-6d4a-4d3e-9a2f-8d0e9c4c1f01")				# 🧬 Неймспейс UUIDv5 для sha256
    _NS_URL = uuid.NAMESPACE_URL												# 🌐 Неймспейс UUIDv5 для URL

    def __init__(
        self,
        downloader: ImageDownloader,
        ocr_service: OCRService,
        generator_factory: TableGeneratorFactory,
        size_chart_finder: ISizeChartFinder,
        product_gender_detector: YoungLAProductGenderDetector,
        general_cache: Optional[GeneralChartCache] = None,
        on_progress: Optional[Union[ProgressCallback, ProgressFn]] = None,
    ) -> None:
        """
        ⚙️ Ініціалізує залежності та конфігурацію сервісу.

        Args:
            downloader (ImageDownloader): Сервіс завантаження зображень.
            ocr_service (OCRService): OCR-сервіс для розпізнавання.
            generator_factory (TableGeneratorFactory): Фабрика генераторів PNG.
            size_chart_finder (ISizeChartFinder): Пошуковик таблиць у HTML.
            product_gender_detector (YoungLAProductGenderDetector): Детектор статі товару.
            general_cache (GeneralChartCache | None): Кеш men/women PNG (опційно).
            on_progress (ProgressCallback | ProgressFn | None): Зовнішній слухач прогресу.
        """
        self.downloader = downloader											# ⬇️ Провайдер завантажень
        self.ocr_service = ocr_service											# 🔤 OCR-сервіс
        self.generator_factory = generator_factory								# 🖼️ Фабрика генераторів
        self.finder = size_chart_finder										# 🔎 Пошуковик таблиць
        self._product_gender_detector = product_gender_detector				# 🚻 Визначення статі товару
        self.on_progress: Union[ProgressCallback, ProgressFn] = on_progress or (lambda *_a, **_k: None)	# 🔔 Колбек оновлень
        self._cfg = ConfigService()											# ⚙️ Глобальна конфігурація
        self._task_meta: Dict[asyncio.Task, Dict[str, Any]] = {}				# 📌 Реєстр активних задач
        self._general_cache = general_cache or GeneralChartCache(self._GENERAL_CACHE_DIR)	# 💾 Кеш універсальних PNG

        cpu = max(1, os.cpu_count() or 1)										# 🧮 Логічні ядра CPU

        dl_auto = max(2, min(16, min(8, 2 * cpu)))								# 🔧 Автоліміт завантажень
        dl_cfg = cast(Optional[int], self._cfg.get("size_chart.concurrency.download.max", None, int))	# ⚙️ Конфігурація завантажень
        dl_min = cast(int, self._cfg.get("size_chart.concurrency.download.min", 2, int) or 2)			# 🪙 Мінімальний IO-паралелізм
        dl_cap = cast(int, self._cfg.get("size_chart.concurrency.download.max_cap", 16, int) or 16)	# 🧱 Верхня межа IO
        env_dl = os.getenv("SIZE_CHART_DL_MAX")									# 🌐 Env-override для IO
        if env_dl and env_dl.isdigit():										# 🌐 Якщо задано env — воно має пріоритет
            self._dl_max = int(env_dl)											# 🔌 Жорстке значення з env
        else:
            self._dl_max = dl_cfg if dl_cfg is not None else dl_auto			# ⚙️ Конфігурація чи авто
        self._dl_max = max(dl_min, min(dl_cap, self._dl_max))					# 🧮 Затискаємо в межах

        ocr_auto = max(1, min(8, cpu // 2))									# 🔧 Автоліміт для CPU/API
        ocr_cfg = cast(Optional[int], self._cfg.get("size_chart.concurrency.ocr.max", None, int))		# ⚙️ Конфігурація генерації/OCR
        ocr_min = cast(int, self._cfg.get("size_chart.concurrency.ocr.min", 1, int) or 1)				# 🪙 Мінімальний CPU-паралелізм
        ocr_cap = cast(int, self._cfg.get("size_chart.concurrency.ocr.max_cap", 8, int) or 8)			# 🧱 Верхня межа CPU
        env_ocr = os.getenv("SIZE_CHART_OCR_MAX")								# 🌐 Env-override для OCR
        if env_ocr and env_ocr.isdigit():									# 🌐 Якщо задано env — воно має пріоритет
            self._ocr_max = int(env_ocr)										# 🔌 Жорстке значення з env
        else:
            self._ocr_max = ocr_cfg if ocr_cfg is not None else ocr_auto		# ⚙️ Конфігурація чи авто
        self._ocr_max = max(ocr_min, min(ocr_cap, self._ocr_max))				# 🧮 Затискаємо в межах

        if self._LEGACY_MAX_CONCURRENCY > 0:									# 🪢 Історичне загальне обмеження
            self._dl_max = min(self._dl_max, self._LEGACY_MAX_CONCURRENCY)		# 🔗 Узгоджуємо з legacy
            self._ocr_max = min(self._ocr_max, max(1, self._LEGACY_MAX_CONCURRENCY // 2))

        logger.info("⚙️ SizeChart concurrency: download=%s, ocr=%s (cpu=%s)", self._dl_max, self._ocr_max, cpu)

        self._autotune_enabled = bool(self._cfg.get("size_chart.concurrency.autotune.enabled", False, bool))	# 🤖 Чи вмикати автотюнер
        self._autotune_window = int(self._cfg.get("size_chart.concurrency.autotune.window", 50, int) or 50)		# 📊 Розмір буфера p95
        self._autotune_cooldown_s = float(self._cfg.get("size_chart.concurrency.autotune.cooldown_s", 30, float) or 30.0)	# 🧊 Перерва між підказками
        self._dl_durations: deque[float] = deque(maxlen=self._autotune_window)	# 🕒 Спостереження за IO
        self._ocr_durations: deque[float] = deque(maxlen=self._autotune_window)	# 🕒 Спостереження за CPU
        self._last_tune_ts = 0.0												# 🕰️ Час останньої підказки

    @classmethod
    def _make_task_id(cls, *, url: str, sha256: Optional[str]) -> str:
        """
        🆔 Генерує стабільний UUIDv5 для задачі.

        Args:
            url (str): Початковий URL.
            sha256 (str | None): Контентний хеш (якщо відомий).

        Returns:
            str: UUIDv5, стабільний між запусками.
        """
        try:
            if sha256:													# 🧮 Якщо відомий хеш — використовуємо його
                return str(uuid.uuid5(cls._NS_SHA, sha256.lower()))			# 🧬 ID за контентом
            return str(uuid.uuid5(cls._NS_URL, url))							# 🌐 ID за URL
        except Exception:
            base = (sha256 or url or "")[:32] or uuid.uuid4().hex			# 🛟 Фолбек до випадкового значення
            return uuid.uuid5(cls._NS_SHA, base).hex							# 🧬 Стабільний фолбек

    # ================================
    # 📣 ПУБЛІЧНИЙ API
    # ================================
    async def process_all_size_charts(
        self,
        page_source: str,
        product_sku: Optional[str] = None,
        on_progress: Optional[ProgressFn] = None,
    ) -> List[str]:
        """Оркеструє повний цикл пошуку/обробки size-chart для переданого HTML.

        Args:
            page_source: Сирий HTML сторінки товару.
            product_sku: Артикул, який допомагає точніше знайти таблиці.
            on_progress: Опційний callback прогресу.
        """

        original_callback = self.on_progress									# 🔁 Зберігаємо поточний колбек
        if on_progress is not None:										# 🔄 Підміняємо глобальний колбек на локальний
            self.on_progress = on_progress										# 🎯 Тимчасово підміняємо його

        try:
            if not page_source or not isinstance(page_source, str):		# 🚫 Валідуємо, що HTML коректний
                logger.warning("⚠️ Передано порожній або некоректний page_source.")
                return []													# ↩️ Немає сенсу продовжувати

            product_gender = self._product_gender_detector.detect(page_source)	# 🚻 Визначаємо стать товару
            logger.debug("🚻 Визначена стать товару: %s", product_gender.value)

            current_task = asyncio.current_task()							# 🔍 Отримуємо поточну корутину
            if current_task is not None and current_task.cancelled():		# 🛑 Обробка була скасована до старту
                logger.info("🛑 Обробку скасовано до старту.")
                return []													# ↩️ Пайплайн уже скасований

            started_at = time.time()										# 🕒 Запам'ятовуємо час початку
            images_to_process = self.finder.find_images(
                page_source,
                product_sku=product_sku,
            )		# 🔎 Шукаємо кандидати з урахуванням SKU
            if not images_to_process:										# ℹ️ Немає що обробляти
                logger.info("ℹ️ Таблиці розмірів не знайдено.")
                return []													# ↩️ Пустий результат без помилок

            tmp_dir = Path(self._TMP_DIR_NAME)								# 📁 Каталог тимчасових файлів
            tmp_dir.mkdir(parents=True, exist_ok=True)						# 🧱 Створюємо при потребі
            logger.info("🔎 Знайдено %d зображень для обробки", len(images_to_process))

            sem_dl = asyncio.Semaphore(max(1, self._dl_max))				# 🔐 Обмеження IO-завдань
            sem_ocr = asyncio.Semaphore(max(1, self._ocr_max))				# 🔐 Обмеження CPU/OCR-завдань

            tasks: List[asyncio.Task[Optional[str]]] = []					# 📋 Реєстр асинхронних задач
            general_variants_seen: Set[GeneralChartVariant] = set()			# 🚫 Уникаємо дублювання універсальних таблиць
            for idx, (url, chart_type) in enumerate(images_to_process):	# 🔄 Плануємо окрему корутину на кожний URL
                general_variant: Optional[GeneralChartVariant] = None
                if chart_type is ChartType.GENERAL:
                    general_variant = self._detect_general_variant(url)
                    if general_variant:
                        if not self._general_variant_allowed(general_variant, product_gender):
                            logger.debug(
                                "↩️ Пропущено універсальну таблицю %s для продукту %s",
                                general_variant.value,
                                product_gender.value,
                            )
                            continue
                        if general_variant in general_variants_seen:
                            logger.debug("↩️ Пропущено повтор універсальної таблиці (%s)", general_variant.value)
                            continue
                        general_variants_seen.add(general_variant)
                task_id = self._make_task_id(url=url, sha256=None)			# 🆔 Перший стабільний ID
                task = asyncio.create_task(									# 🚀 Стартуємо окрему корутину
                    self._process_one(
                        idx,
                        url,
                        chart_type,
                        tmp_dir,
                        sem_dl,
                        sem_ocr,
                        task_id,
                        general_variant=general_variant,
                    )
                )
                self._task_meta[task] = {									# 🗂️ Зберігаємо метадані для скасування
                    "idx": idx,
                    "url": url,
                    "chart_type": chart_type,
                    "started_at": time.time(),
                    "task_id": task_id,
                    "general_variant": general_variant.value if general_variant else None,
                }
                task.add_done_callback(lambda done_task: self._task_meta.pop(done_task, None))	# 🧹 Очищаємо після завершення
                tasks.append(task)

            try:
                raw_results: List[Union[Optional[str], BaseException]] = await asyncio.gather(
                    *tasks,
                    return_exceptions=True,
                )															# 🧺 Збираємо результати й помилки
            except asyncio.CancelledError:
                logger.info(
                    "🛑 Скасування пайплайна: позначаємо активні задачі як DONE(cancelled) та зупиняємо %d корутин(и)…",
                    len(tasks),
                )

                for task, meta in list(self._task_meta.items()):			# 📣 Сповіщаємо всі активні задачі
                    if not task.done():
                        try:
                            await self._emit_progress(
                                idx=meta["idx"],
                                url=meta["url"],
                                chart_type=meta["chart_type"],
                                stage=Stage.DONE,
                                started_at=meta["started_at"],
                                error="cancelled",
                                task_id=meta.get("task_id", ""),
                            )
                        except Exception:
                            pass

                _inc_cancelled()											# 🧮 Фіксуємо скасування в метриках

                for task in tasks:
                    task.cancel()											# 🛑 Скасовуємо всі корутини
                await asyncio.gather(*tasks, return_exceptions=True)		# ⏳ Чекаємо коректного завершення
                raise														# 🚨 Прокидаємо скасування далі

            success_paths: List[str] = []									# 📦 Список успішних PNG
            for result in raw_results:										# 📦 Розбираємо відповіді gather
                if isinstance(result, BaseException):						# ⚠️ Підзадача завершилась помилкою
                    logger.warning("⚠️ Підзадача завершилася помилкою: %s", result)
                    continue												# ❌ Пропускаємо невдалий результат
                if result:
                    success_paths.append(result)								# ✅ Додаємо шлях до готового PNG

            logger.info(
                "✅ Оброблено %d/%d таблиць за %.2f сек.",
                len(success_paths),
                len(images_to_process),
                time.time() - started_at,
            )
            return success_paths											# ↩️ Повертаємо список результатів

        finally:
            self.on_progress = original_callback							# 🔄 Відновлюємо глобальний колбек

    # ================================
    # 🔔 ПРОГРЕС
    # ================================
    async def _emit_progress(
        self,
        *,
        idx: int,
        url: str,
        chart_type: ChartType,
        stage: Stage,
        started_at: float,
        path: Optional[str] = None,
        error: Optional[str] = None,
        bytes_downloaded: Optional[int] = None,
        sha256: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
        task_id: str,
    ) -> None:
        """
        🔔 Надійно викликає зовнішній колбек прогресу.

        Args:
            idx (int): Порядковий номер задачі.
            url (str): Джерельний URL.
            chart_type (ChartType): Тип таблиці.
            stage (Stage): Поточний етап.
            started_at (float): Час старту задачі.
            path (str | None): Шлях до файлу (якщо є).
            error (str | None): Опис помилки.
            bytes_downloaded (int | None): Обсяг завантажених даних.
            sha256 (str | None): Хеш контенту.
            extra (dict[str, Any] | None): Додаткова інформація.
            task_id (str): Стабільний ідентифікатор задачі.
        """
        payload = SizeChartProgress(
            idx=idx,
            url=url,
            chart_type=chart_type,
            stage=stage,
            started_at=started_at,
            elapsed=max(0.0, time.time() - started_at),
            path=path,
            error=error,
            bytes_downloaded=bytes_downloaded,
            sha256=sha256,
            task_id=task_id,
            extra=extra or {},
        )
        maybe_coro = cast(Any, self.on_progress)(payload)					# 🔄 Викликаємо користувацький колбек
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro												# ⏳ Чекаємо завершення корутини

    # ================================
    # ⚙️ ОБРОБКА ОКРЕМОГО ЗОБРАЖЕННЯ
    # ================================
    async def _process_one(
        self,
        idx: int,
        img_url: str,
        chart_type: ChartType,
        tmp_dir: Path,
        sem_dl: asyncio.Semaphore,
        sem_ocr: asyncio.Semaphore,
        task_id: str,
        general_variant: Optional[GeneralChartVariant] = None,
    ) -> Optional[str]:
        """
        🔄 Повний конвеєр обробки одного зображення.

        Args:
            idx (int): Порядковий номер задачі.
            img_url (str): Посилання на зображення таблиці.
            chart_type (ChartType): Тип таблиці розмірів.
            tmp_dir (Path): Каталог для тимчасових файлів.
            sem_dl (asyncio.Semaphore): Семафор для IO.
            sem_ocr (asyncio.Semaphore): Семафор для OCR/генерації.
            task_id (str): Стабільний ідентифікатор задачі.

        Returns:
            Optional[str]: Шлях до готового PNG або None, якщо стався збій.
        """
        async with sem_dl:													# 🔐 IO-критична секція з обмеженим паралелізмом
            started_at = time.time()										# ⏱️ Позначка старту
            human_title = f"[{idx + 1}] {img_url}"							# 📝 Френдлі-ідентифікатор у логах
            logger.info("▶️ [task=%s] Старт обробки %s (type=%s)", task_id, human_title, chart_type.value)

            await self._emit_progress(
                idx=idx,
                url=img_url,
                chart_type=chart_type,
                stage=Stage.START,
                started_at=started_at,
                task_id=task_id,
            )

            if general_variant is not None:
                cached_path = self._general_cache.get_cached_path(general_variant)
                if cached_path:
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DONE,
                        started_at=started_at,
                        path=cached_path,
                        task_id=task_id,
                        extra={
                            "general_variant": general_variant.value,
                            "cache_hit": True,
                        },
                    )
                    return cached_path

            try:
                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.DOWNLOAD_START,
                    started_at=started_at,
                    task_id=task_id,
                )
                extension = self._guess_ext(img_url)						# 🧩 Визначаємо розширення
                download_path = tmp_dir / f"download_{idx}{extension}"		# 📁 Шлях для завантаження

                download_started = time.time()								# 🕒 Фіксуємо час початку завантаження
                outcome: DownloadOutcome = await self.downloader.download_info(img_url, download_path)
                download_duration = max(0.0, time.time() - download_started)
                if self._autotune_enabled:									# 🤖 Якщо автотюнер ввімкнено — накопичуємо заміри
                    self._dl_durations.append(download_duration)			# 🧮 Збираємо статистику IO

                if isinstance(outcome, DownloadResult):					# ✅ Завантаження успішне — маємо шлях
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DOWNLOAD_OK,
                        started_at=started_at,
                        path=str(outcome.path),
                        bytes_downloaded=outcome.bytes_written,
                        sha256=outcome.sha256,
                        task_id=task_id,
                        extra={
                            "download_status": "ok",
                            "content_type": outcome.content_type,
                            "content_length": outcome.content_length,
                            "bytes_downloaded": outcome.bytes_written,
                            "bytes_written": outcome.bytes_written,
                            "sha256": outcome.sha256,
                            "content_id": self._make_task_id(url=img_url, sha256=outcome.sha256),
                        },
                    )
                    downloaded_path = outcome.path						# 📥 Шлях до завантаженого файлу
                else:														# ❌ Повернувся код помилки завантаження
                    err_code = getattr(outcome, "name", None) or getattr(outcome, "value", None) or str(outcome)
                    logger.warning("⛔ [task=%s] Пропущено (download error=%s): %s", task_id, err_code, human_title)
                    _inc_dl_err(str(err_code))
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DOWNLOAD_FAIL,
                        started_at=started_at,
                        error=f"download:{err_code}",
                        task_id=task_id,
                        extra={"download_status": "fail", "download_error": err_code},
                    )
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DONE,
                        started_at=started_at,
                        error=f"download:{err_code}",
                        task_id=task_id,
                    )
                    return None

                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.OCR_START,
                    started_at=started_at,
                    task_id=task_id,
                )
                ocr_started = time.time()									# 🕒 Початок OCR
                async with sem_ocr:											# 🔐 OCR/CPU секція з власним лімітом
                    ocr_result: SizeChartOcrResult = await self.ocr_service.recognize(
                        str(downloaded_path),
                        cast(PromptChartType, chart_type),
                    )
                ocr_duration = max(0.0, time.time() - ocr_started)
                if self._autotune_enabled:									# 🤖 Оновлюємо статистику OCR
                    self._ocr_durations.append(ocr_duration)				# 🧮 Статистика OCR

                if ocr_result.status != SizeChartOcrStatus.OK:				# ❌ OCR не розпізнав таблицю
                    logger.warning(
                        "⛔ [task=%s] OCR не розпізнав дані %s (status=%s, err=%s)",
                        task_id,
                        human_title,
                        ocr_result.status.value,
                        ocr_result.error,
                    )
                    _inc_ocr_err(ocr_result.status.value)
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.OCR_FAIL,
                        started_at=started_at,
                        error=ocr_result.status.value,
                        task_id=task_id,
                        extra={"ocr_status": ocr_result.status.value, "ocr_error": ocr_result.error},
                    )
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DONE,
                        started_at=started_at,
                        error=ocr_result.status.value,
                        task_id=task_id,
                        extra={"ocr_status": ocr_result.status.value},
                    )
                    return None

                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.OCR_OK,
                    started_at=started_at,
                    task_id=task_id,
                    extra={"ocr_status": ocr_result.status.value},
                )

                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.GENERATE_START,
                    started_at=started_at,
                    task_id=task_id,
                )
                output_path = str(tmp_dir / f"generated_{idx}.png")			# 🖼️ Кінцевий PNG
                try:														# 🧪 Генеруємо PNG на основі даних OCR
                    async with sem_ocr:									# 🔐 Генератор теж використовує CPU-ліміт
                        generator = self.generator_factory.create_generator(
                            chart_type=chart_type,
                            data=ocr_result.data or {},
                            path=output_path,
                        )
                except Exception as factory_err:							# ❌ Створення генератора не вдалося
                    message = f"factory_error: {factory_err}"
                    logger.exception("❌ [task=%s] Помилка фабрики генераторів для %s: %s", task_id, human_title, factory_err)
                    _inc_gen_err("factory_error")
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.GENERATE_FAIL,
                        started_at=started_at,
                        error=message,
                        task_id=task_id,
                    )
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DONE,
                        started_at=started_at,
                        error=message,
                        task_id=task_id,
                    )
                    return None

                try:														# 🖼️ Запускаємо сам рендер PNG
                    generate_started = time.time()							# 🕒 Початок генерації PNG
                    async with sem_ocr:
                        result_path = await generator.generate()
                    generate_duration = max(0.0, time.time() - generate_started)
                    if self._autotune_enabled:
                        self._ocr_durations.append(generate_duration)		# 🧮 Статистика генерації
                except Exception as generate_err:							# ❌ Помилка під час рендеру PNG
                    message = f"generate_error: {generate_err}"
                    logger.exception("❌ [task=%s] Помилка генерації PNG для %s: %s", task_id, human_title, generate_err)
                    _inc_gen_err("generate_error")
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.GENERATE_FAIL,
                        started_at=started_at,
                        error=message,
                        task_id=task_id,
                    )
                    await self._emit_progress(
                        idx=idx,
                        url=img_url,
                        chart_type=chart_type,
                        stage=Stage.DONE,
                        started_at=started_at,
                        error=message,
                        task_id=task_id,
                    )
                    return None

                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.GENERATE_OK,
                    started_at=started_at,
                    path=result_path,
                    task_id=task_id,
                )
                logger.info("✅ [task=%s] Готово %s → %s (%.2fs)", task_id, human_title, result_path, time.time() - started_at)

                if general_variant is not None:
                    cached_target = self._general_cache.store_result(general_variant, result_path)
                    logger.debug(
                        "💾 Кеш універсальної таблиці оновлено (%s → %s)",
                        result_path,
                        cached_target,
                    )

                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.DONE,
                    started_at=started_at,
                    path=result_path,
                    task_id=task_id,
                    extra=({"general_variant": general_variant.value} if general_variant else None),
                )

                if self._autotune_enabled:									# 🤖 Збираємо метрики генератора
                    self._maybe_log_autotune_hint()							# 🤖 Підказка щодо тюнінгу

                return result_path											# ✅ Повертаємо шлях до PNG

            except asyncio.CancelledError:
                logger.info("🛑 [task=%s] Підзадачу скасовано: %s", task_id, human_title)
                await self._emit_progress(
                    idx=idx,
                    url=img_url,
                    chart_type=chart_type,
                    stage=Stage.DONE,
                    started_at=started_at,
                    error="cancelled",
                    task_id=task_id,
                )
                raise														# 🚨 Прокидаємо скасування далі

    # ================================
    # 🔎 УТИЛІТИ
    # ================================
    @staticmethod
    def _guess_ext(url: str) -> str:
        """
        🔍 Грубо визначає розширення файлу за URL.

        Args:
            url (str): Джерельний URL зображення.

        Returns:
            str: Розширення (дефолт — `.png`).
        """
        lowered = (url or "").lower()
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
            if lowered.endswith(ext):
                return ext													# ✅ Знайшли відоме розширення
        return ".png"														# 🔁 Фолбек до PNG

    @staticmethod
    def _detect_general_variant(url: str) -> Optional[GeneralChartVariant]:
        """Визначає тип універсальної таблиці за URL."""
        lowered = (url or "").lower()
        # ⚠️ Спочатку перевіряємо жіночі патерни, щоб «women-size-chart» не
        # матчило по підрядку «men-size-chart» і не відкидалося як MEN.
        if any(pattern in lowered for pattern in _GENERAL_WOMEN_PATTERNS):
            return GeneralChartVariant.WOMEN
        if any(pattern in lowered for pattern in _GENERAL_MEN_PATTERNS):
            return GeneralChartVariant.MEN
        return None

    @staticmethod
    def _general_variant_allowed(variant: GeneralChartVariant, gender: ProductGender) -> bool:
        """
        🚻 Перевіряє, чи відповідає універсальна таблиця статі товару.
        """
        if gender is ProductGender.UNKNOWN:
            return True
        if gender is ProductGender.MEN:
            return variant is GeneralChartVariant.MEN
        if gender is ProductGender.WOMEN:
            return variant is GeneralChartVariant.WOMEN
        return True

    def _maybe_log_autotune_hint(self) -> None:
        """
        🤖 Періодично пише у лог підказку з p95 тривалостей (IMP-047).
        """
        now = time.time()
        if now - self._last_tune_ts < self._autotune_cooldown_s:
            return															# ⏳ Ще рано для нової підказки
        self._last_tune_ts = now											# 🕰️ Запам'ятовуємо час виклику

        dl_p95 = self._p95(self._dl_durations)
        ocr_p95 = self._p95(self._ocr_durations)
        if dl_p95 is None and ocr_p95 is None:							# 💤 Даних недостатньо для поради
            return															# 💤 Недостатньо даних

        parts: List[str] = []
        if dl_p95 is not None:
            parts.append(f"download p95≈{dl_p95:.2f}s (N={len(self._dl_durations)})")	# 📊 Статистика завантажень
        if ocr_p95 is not None:
            parts.append(f"ocr/gen p95≈{ocr_p95:.2f}s (N={len(self._ocr_durations)})")	# 📊 Статистика OCR/генерації

        logger.info("🧪 autotune: %s | limits: dl=%s, ocr=%s", ", ".join(parts), self._dl_max, self._ocr_max)

    @staticmethod
    def _p95(values: deque[float]) -> Optional[float]:
        """
        📈 Обчислює приблизне значення p95 для накопичених тривалостей.

        Args:
            values (deque[float]): Колекція замірів.

        Returns:
            float | None: Оцінка p95 або None, якщо даних замало.
        """
        if not values:													# 💤 Ще не накопичили статистику
            return None													# ↩️ Немає статистики
        sorted_values = sorted(values)									# 📊 Сортуємо для p95
        index = max(0, int(0.95 * (len(sorted_values) - 1)))				# 🔢 Обчислюємо індекс p95
        return float(sorted_values[index])								# 📈 Повертаємо значення
