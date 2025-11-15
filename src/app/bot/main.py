# 🤖 app/bot/main.py
"""
🤖 Entry-point Telegram застосунку YoungLA Ukraine.

🔹 Готує середовище (CLI-флаги → ENV) та ініціалізує DI-контейнер, Application PTB.
🔹 Реєструє всі обробники й глобальний error-handler, запускає `run_polling`.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from dotenv import load_dotenv											# 🌱 Завантаження змінних оточення з .env
from telegram.ext import Application, ApplicationBuilder, ContextTypes					# 🤖 PTB v21 Application API

# 🔠 Системні імпорти
import logging															# 🧾 Логування подій запуску
import os																# 🌍 Робота з оточенням/ENV
import sys																# 🧵 CLI-аргументи та sys.path
from pathlib import Path													# 🛤️ Шлях до кореня репозиторію
from typing import Optional													# 🧮 Анотації Optional

# 🧩 Внутрішні модулі проєкту
from app.bot.services import CustomContext									# 🧠 Кастомний PTB-контекст
from app.config.config_service import ConfigService								# ⚙️ Завантаження конфігів
from app.config.setup.bot_registrar import BotRegistrar								# 📋 Реєстрація хендлерів
from app.shared.utils.logger import LOG_NAME									# 🏷️ Ім'я кореневого логера


# ================================
# 🏗️ PATH & ЛОГУВАННЯ
# ================================
ROOT_PATH = Path(__file__).resolve().parents[2]										# 🛤️ Корінь репозиторію (src/)
if str(ROOT_PATH) not in sys.path:											# 🔗 Гарантуємо доступ до src/ при прямому запуску
    sys.path.insert(0, str(ROOT_PATH))										# ➕ Додаємо шлях до sys.path

IMPORT_ERROR: Optional[Exception] = None										# 🧷 Зберігаємо причину помилки імпорту контейнера
try:
    from app.config.setup.container import bootstrap_logging, Container					# 🚀 Ініціалізація логування + DI-контейнер
except Exception as error:													# 🧯 Фолбек, якщо контейнер недоступний
    IMPORT_ERROR = error													# 🧾 Зберігаємо виняток для подальшого репорту
    Container = None  # type: ignore[misc, assignment]								# 🚫 Позначаємо відсутність контейнера

    def bootstrap_logging() -> logging.Logger:									# 🧰 Локальний фолбек-логер
        return logging.getLogger(__name__)									# 🔁 Повертаємо стандартний логер

bootstrap_logging()														# 🪵 Піднімаємо YAML-конфіг логування


# ================================
# 🪵 ГЛОБАЛЬНИЙ ЛОГЕР
# ================================
logger = logging.getLogger(LOG_NAME)											# 🧾 Використовуємо централізоване ім'я логера
logger.debug("🧭 main.py завантажено, ROOT_PATH=%s", ROOT_PATH)								# 🧭 Фіксуємо шлях і факт імпорту


# ================================
# 🧩 DI / APPLICATION BUILDER
# ================================
def build_application(token: str) -> Application:
    """
    Створює та повертає PTB Application із зареєстрованими обробниками.
    """
    logger.info("🔧 Створюємо ConfigService для DI")									# 🔧 Лог процесу ініціалізації конфігів
    config = ConfigService()														# ⚙️ Завантажуємо конфіги

    if Container is None:  # pragma: no cover
        logger.critical("🚨 Container недоступний: %s", IMPORT_ERROR)							# 🚨 Повідомляємо про відсутність контейнера
        raise RuntimeError("Container module is required to build the bot.") from IMPORT_ERROR		# ⛔ Пояснюємо причину

    logger.debug("🧱 Створюємо DI-контейнер")											# 🧱 Лог створення контейнера
    container = Container(config)													# 🧩 Інстансуємо контейнер

    logger.debug("🤖 Будуємо Application через ApplicationBuilder")								# 🤖 Лог побудови PTB Application
    application = (
        ApplicationBuilder()
        .token(token)														# 🔑 Передаємо токен
        .context_types(ContextTypes(context=CustomContext))								# 🧠 Підключаємо CustomContext
        .build()															# 🏗️ Створюємо Application
    )

    application.bot_data["container"] = container										# 📦 Зберігаємо контейнер для дебагу/тестів
    logger.debug("📦 Контейнер додано до bot_data")											# 🧾 Лог факту

    registrar = BotRegistrar(application, container)									# 📋 Ініціалізуємо реєстратор хендлерів
    logger.info("🧾 Реєструємо обробники Telegram")										# 🧾 Старт реєстрації
    registrar.register_handlers()													# ✅ Реєструємо всі хендлери

    async def _on_error(update, context) -> None:
        """
        Глобальний error-handler PTB: відправляє винятки у централізований сервіс.
        """
        err: Optional[Exception] = getattr(context, "error", None)							# 🧷 Витягуємо виняток із контексту
        if err is None:															# ⚠️ Якщо помилки немає — нічого не робимо
            logger.debug("ℹ️ _on_error викликано без context.error")							# 📄 Лог ситуації
            return																# 🔚 Вихід
        logger.error("🔥 Виняток у PTB: %s", err, exc_info=True)								# 🔥 Логуємо помилку
        try:
            await container.exception_handler_service.handle(err, update)						# 🛡️ Доручаємо централізованому сервісу
        except Exception as nested:  # noqa: BLE001
            logger.exception("💥 Global error handler failed: %s", nested)						# 💥 Якщо навіть хендлер впав

    application.add_error_handler(_on_error)											# 🧩 Реєструємо глобальний error-handler
    logger.info("✅ Application готовий до запуску")											# ✅ Завершили підготовку
    return application														# 📤 Повертаємо інстанс


# ================================
# ⚙️ CLI-ФЛАГИ → ENV
# ================================
def _apply_cli_flags_to_env(args: list[str]) -> None:
    """
    Мапить зручні CLI-прапорці на ENV змінні Playwright/бота.
    """
    logger.debug("🧾 Обробляємо CLI-флаги: %s", args)											# 🧾 Фіксуємо список аргументів

    def has_flag(flag: str) -> bool:
        return any(arg == flag for arg in args)										# 🔍 Перевіряємо наявність флага

    def value(prefix: str) -> Optional[str]:
        for arg in args:														# 🔁 Перебираємо аргументи
            if arg.startswith(prefix + "="):										# 📎 Шукаємо аргумент за префіксом
                return arg.split("=", 1)[1]										# 📤 Повертаємо значення після "="
        return None															# 🚫 Значення не знайдено

    if has_flag("--headful"):													# 👀 Режим headful
        os.environ["APP_PLAYWRIGHT_HEADLESS"] = "false"									# ⚙️ Вимикаємо headless
        logger.info("🖥️ Запускаємо у headful-режимі")										# 🖥️ Лог
    if has_flag("--headless"):													# 😴 Режим headless
        os.environ["APP_PLAYWRIGHT_HEADLESS"] = "true"									# ⚙️ Вмикаємо headless
        logger.info("🙈 Примусово headless-режим")											# 🙈 Лог

    if has_flag("--devtools"):													# 🛠️ Підключення Playwright devtools WS
        os.environ["APP_PLAYWRIGHT_DEVTOOLS_ENABLED"] = "true"							# ✅ Увімкнути devtools
        os.environ.setdefault("APP_PLAYWRIGHT_DEVTOOLS_MODE", "playwright")					# 🧮 Використати стандартний режим
        logger.info("🛠️ Devtools (playwright) увімкнено")									# 🛠️ Лог

    if any(arg.startswith("--devtools-cdp") for arg in args):								# 🌐 Режим CDP
        os.environ["APP_PLAYWRIGHT_DEVTOOLS_ENABLED"] = "true"							# ✅ Devtools
        os.environ["APP_PLAYWRIGHT_DEVTOOLS_MODE"] = "cdp"								# 🌐 Режим CDP
        port = value("--devtools-cdp")												# 🔢 Витягуємо порт (якщо заданий)
        if port and port.isdigit():												# ✅ Перевіряємо валідність
            os.environ["APP_PLAYWRIGHT_DEVTOOLS_REMOTE_DEBUGGING_PORT"] = port					# 🚪 Встановлюємо порт
            logger.info("🌐 Devtools (CDP) порт=%s", port)									# 🌐 Лог

    channel = value("--channel")													# 🎯 Браузерний канал
    if channel:																# ✅ Якщо вказаний
        os.environ["APP_PLAYWRIGHT_LAUNCH_CHANNEL"] = channel								# 🔁 Передаємо Playwright
        logger.info("🛰️ Запускаємо браузерний канал: %s", channel)							# 🛰️ Лог

    trace_mode = value("--trace")													# 🧶 Трасування
    if trace_mode:															# ✅ Якщо вказано
        os.environ["APP_PLAYWRIGHT_TRACE_ENABLED"] = "true"								# ✅ Увімкнути trace
        normalized = "on" if trace_mode.lower() == "on" else "retain-on-failure"					# 🧮 Нормалізуємо значення
        os.environ["APP_PLAYWRIGHT_TRACE_MODE"] = normalized								# 🧵 Задаємо режим
        logger.info("🧵 Trace mode = %s", normalized)										# 🧵 Лог

    if has_flag("--headful") and has_flag("--headless"):									# ⚠️ Конфліктний випадок
        logger.warning("⚠️ Виявлено одночасно --headful та --headless. Пріоритет за останнім флагом.")			# ⚠️ Попередження


# ================================
# 🚀 ENTRYPOINT
# ================================
def run() -> None:
    """
    Основна точка входу: парсить CLI-флаги, читає токен і запускає бота.
    """
    args = list(sys.argv[1:])												# 📥 Зчитуємо CLI-аргументи
    _apply_cli_flags_to_env(args)												# 🔁 Мапимо флаги на ENV

    load_dotenv()															# 🌱 Завантажуємо змінні з .env
    logger.debug("🌱 .env завантажено")												# 📒 Лог

    token = (
        os.getenv("BOT_TOKEN")												# 🔑 Перевага локальному токену
        or os.getenv("TELEGRAM_BOT_TOKEN")										# 🔑 Альтернатива
        or os.getenv("TELEGRAM_TOKEN")											# 🔑 Ще один варіант
    )
    if not token:															# 🛡️ Якщо ENV порожні
        logger.warning("⚠️ Токен в ENV не знайдено, читаємо з конфігів")							# ⚠️ Лог
        token = ConfigService().get("telegram.bot.token")								# 🔐 Читаємо з config_service
    if not token:															# 🚨 Якщо немає навіть у конфігах
        logger.critical("🚨 Не знайдено токен Telegram")									# 🚨 Лог
        raise RuntimeError("Set BOT_TOKEN (or TELEGRAM_BOT_TOKEN) in environment.")					# ⛔ Помилка

    application = build_application(token)											# 🧩 Будуємо Application
    logger.info("🤖 Bot is starting…")												# 🚀 Старт
    application.run_polling()													# 🏃 Запускаємо полінг
    logger.info("👋 Bot stopped")													# 🛑 Завершення


if __name__ == "__main__":														# ▶️ Дозволяє запуск як скрипт
    run()																# 🚀 Стартуємо бота
