import logging
import re

import httpx
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from config import settings

logger = logging.getLogger(__name__)
REEL_REGEX = re.compile(r"https?://(www\.)?instagram\.com/reel/[^\s]+", re.IGNORECASE)


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.effective_message.text if update.effective_message else ""
    if not text:
        return
    match = REEL_REGEX.search(text)
    if not match:
        return

    url = match.group(0)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{context.bot_data['api_base_url']}/api/webhook/reel",
                json={"url": url, "secret": settings.webhook_secret},
            )
            data = resp.json()
        await update.effective_message.reply_text(f"Submitted: {data}")
    except Exception as exc:
        logger.exception("Failed to submit reel from telegram")
        await update.effective_message.reply_text(f"Failed: {exc}")


def run_telegram_bot(api_base_url: str) -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["api_base_url"] = api_base_url.rstrip("/")
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    app.run_polling(close_loop=False)
