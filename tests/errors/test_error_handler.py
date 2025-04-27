"""
🧪 test_error_handler.py — unit-тести для декоратора error_handler

Перевіряє:
- Відповідь на помилки OpenAI
- Відповідь на помилки Selenium
- Відповідь на помилки Telegram
- Відповідь на невідомі винятки
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from errors.error_handler import error_handler
import openai


@pytest.mark.parametrize("exception,log_msg,reply", [
    (Exception("Test error"), "🔥 Невідома критична помилка", "❌ Критична помилка! Повідом адміністратора."),
])
@pytest.mark.asyncio
async def test_error_handler_unknown_exception_logged_and_replied(caplog, exception, log_msg, reply):
    @error_handler
    async def faulty_handler(update, context):
        raise exception

    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    with caplog.at_level(logging.DEBUG):
        await faulty_handler(update, context)

    assert log_msg in caplog.text
    update.message.reply_text.assert_awaited_with(reply)


@pytest.mark.asyncio
async def test_error_handler_openai_quota_error():
    @error_handler
    async def openai_quota_fail(update, context):
        raise openai.RateLimitError(
            "Quota exceeded",  # ← додай це!
            response=MagicMock(),
            body={"error": {"message": "Quota exceeded"}}
        )

    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    await openai_quota_fail(update, MagicMock())
    update.message.reply_text.assert_awaited_with("⚠️ Помилка: недостатньо квоти OpenAI.")


@pytest.mark.asyncio
async def test_error_handler_openai_error_logged_and_replied():
    import openai
    @error_handler
    async def openai_general_fail(update, context):
        raise openai.OpenAIError("general")

    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    await openai_general_fail(update, MagicMock())
    update.message.reply_text.assert_awaited_with("⚠️ OpenAI: general")


@pytest.mark.asyncio
async def test_error_handler_selenium_timeout():
    from selenium.common.exceptions import TimeoutException
    @error_handler
    async def selenium_timeout(update, context):
        raise TimeoutException()

    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    await selenium_timeout(update, MagicMock())
    update.message.reply_text.assert_awaited_with("⚠️ Сторінка завантажується занадто довго.")
