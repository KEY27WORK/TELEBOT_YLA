# 🚨 app/bot/ui/error_presenter.py
"""
🚨 Формує користувацькі повідомлення про помилки.

🔹 Підбирає локалізовані тексти з `static_messages`
🔹 Додає пораду, як діяти далі, залежно від `ReasonCode`
🔹 Підтримує вставки додаткового контексту (HTTP-статус, retry-after тощо)
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
# (відсутні)

# 🔠 Системні імпорти
from typing import Any, Dict, Final                                      # 🧰 Типи та константи

# 🧩 Внутрішні модулі проєкту
from app.bot.ui import static_messages as msg                            # 📝 Локалізовані повідомлення
from app.errors.reason_codes import ReasonCode                           # 🧾 Коди помилок домену


# ================================
# 📝 МАПА ПІДКАЗОК ДЛЯ КОРИСТУВАЧА
# ================================
_NEXT_TIPS: Final[Dict[ReasonCode, str]] = {                             # 💡 Пропозиції наступних кроків
    ReasonCode.LINK_INVALID: "Перевірте посилання і надішліть ще раз.",
    ReasonCode.URL_NOT_PRODUCT: "Надішліть саме посилання на товар, не на колекцію.",
    ReasonCode.PRODUCT_NOT_FOUND: "Спробуйте інший товар або перевірте URL.",
    ReasonCode.OUT_OF_STOCK: "Спробуйте інший розмір/колір або інший регіон.",
    ReasonCode.REGION_NOT_RECOGNIZED: "Надайте посилання на сайт YoungLA з регіоном US/EU/UK.",
    ReasonCode.PARSE_FAILED: "Повторіть спробу пізніше — сайт міг тимчасово не відповісти.",
    ReasonCode.HTTP_TIMEOUT: "Повторіть спробу — можлива повільна мережа.",
    ReasonCode.HTTP_CONNECTION: "Перевірте інтернет, потім спробуйте знову.",
    ReasonCode.HTTP_STATUS: "Перевірте, чи доступна сторінка. Якщо так — повторіть.",
    ReasonCode.TELEGRAM_RETRY_AFTER: "Почекайте кілька секунд і повторіть.",
    ReasonCode.TELEGRAM_GENERAL: "Повторіть спробу трохи пізніше.",
    ReasonCode.AI_RATE_LIMIT: "Повторіть через хвилину.",
    ReasonCode.AI_GENERAL: "Повторіть пізніше.",
    ReasonCode.INTERNAL: "Повторіть спробу. Якщо повторюється — напишіть у підтримку.",
}


# ================================
# 🧾 ГОЛОВНИЙ ФОРМАТЕР ПОВІДОМЛЕНЬ
# ================================
def build_error_message(code: ReasonCode, *, ctx: Dict[str, Any] | None = None) -> str:
    """
    Повертає локалізоване повідомлення про помилку з опціональною порадою.
    """
    context = ctx or {}                                                  # 🧰 Захисний дефолт
    mapping: Dict[ReasonCode, str] = {                                   # 🗺️ Відповідність ReasonCode → статичне повідомлення
        ReasonCode.LINK_INVALID: msg.URL_NOT_RECOGNIZED,
        ReasonCode.URL_NOT_PRODUCT: msg.URL_NOT_PRODUCT,
        ReasonCode.REGION_NOT_RECOGNIZED: msg.ERROR_REGION_NOT_RECOGNIZED,
        ReasonCode.PARSE_FAILED: msg.ERROR_BROWSER_GENERAL,
        ReasonCode.HTTP_TIMEOUT: msg.ERROR_HTTP_TIMEOUT,
        ReasonCode.HTTP_CONNECTION: msg.ERROR_HTTP_CONNECTION,
        ReasonCode.HTTP_STATUS: msg.ERROR_HTTP_STATUS.format(status_code=context.get("status_code", "N/A")),
        ReasonCode.TELEGRAM_RETRY_AFTER: msg.ERROR_TELEGRAM_RETRY_AFTER.format(seconds=context.get("seconds", 1)),
        ReasonCode.TELEGRAM_GENERAL: msg.ERROR_TELEGRAM_GENERAL,
        ReasonCode.AI_RATE_LIMIT: msg.ERROR_AI_RATE_LIMIT,
        ReasonCode.AI_GENERAL: msg.ERROR_AI_GENERAL,
        ReasonCode.PRODUCT_NOT_FOUND: msg.SEARCH_NO_RESULTS,
        ReasonCode.OUT_OF_STOCK: "❌ Немає в наявності у вибраному регіоні.",
        ReasonCode.INTERNAL: msg.ERROR_CRITICAL,
    }

    body = mapping.get(code, msg.ERROR_UNKNOWN)                         # 🧾 Основний текст помилки
    tip = _NEXT_TIPS.get(code)                                          # 💡 Додаткова порада
    if tip:
        return f"{body}\n\n<i>{tip}</i>"                                # 🛟 Додаємо подсказку курсивом
    return body                                                         # 📤 Повертаємо тільки основний текст
