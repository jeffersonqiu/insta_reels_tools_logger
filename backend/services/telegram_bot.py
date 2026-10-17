"""Optional legacy polling entry point. Use the Railway webhook in production."""

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from config import settings
from services.telegram_handler import TelegramUpdate, process_update


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Polling and webhooks share private-chat authorization and durable dedup.
    await process_update(TelegramUpdate.model_validate(update.to_dict()))


def run_telegram_bot(api_base_url: str) -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is missing.')
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data['api_base_url'] = api_base_url.rstrip('/')  # retained for caller compatibility
    app.add_handler(MessageHandler(filters.TEXT, _handle_message))
    app.run_polling(close_loop=False)
