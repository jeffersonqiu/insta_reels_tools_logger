import asyncio
import datetime as dt
import logging
import re

from fastapi import BackgroundTasks
from pydantic import BaseModel, Field, StrictInt

from config import settings
from db.client import get_supabase
from models.schemas import ReelWebhookRequest
from routers.webhook import receive_reel
from services.knowledge_qa import AnswerCreditsError, NO_CREDITS, answer_question, recent_items
from services.telegram_api import reply

logger = logging.getLogger(__name__)
REEL_REGEX = re.compile(r"https?://(?:www\.)?instagram\.com/reel/[^\s<>]+", re.IGNORECASE)
HELP = "Share an Instagram Reel to save it, or ask me naturally about your whole saved repository: content, tools, transcripts and your notes.\n\nTry: What are the latest 3 things worth my time? Compare the agent tools I've saved. What should I try next?\n\n/ask <question> — answer with sources\n/recent — latest saved content\n/help — show this help\n\nRecommendations use saved knowledge and your tool statuses. Each question is independent."


class TelegramUser(BaseModel):
    id: StrictInt
    is_bot: bool = False


class TelegramChat(BaseModel):
    id: StrictInt
    type: str


class TelegramMessage(BaseModel):
    from_user: TelegramUser | None = Field(default=None, alias="from")
    chat: TelegramChat
    text: str | None = Field(default=None, max_length=8192)


class TelegramUpdate(BaseModel):
    update_id: StrictInt = Field(ge=0)
    message: TelegramMessage | None = None


def update_kind(update: TelegramUpdate) -> str:
    message = update.message
    if not message or not message.text or not message.from_user:
        return "ignore"
    if message.chat.type != "private" or message.from_user.is_bot or message.chat.id != message.from_user.id:
        return "ignore"
    allowed = {int(value) for value in settings.telegram_allowed_user_ids.split(",") if value}
    if message.from_user.id in allowed:
        return "process"
    command = message.text.strip().split()[0].split("@")[0].lower() if message.text.strip() else ""
    return "setup" if command == "/start" else "ignore"


def claim_update(update_id: int) -> bool:
    rows = get_supabase().table("telegram_updates").upsert(
        {"update_id": update_id, "status": "processing"},
        on_conflict="update_id", ignore_duplicates=True,
    ).execute().data
    return bool(rows)


def _finish(update_id: int, status: str, error_type: str | None = None) -> None:
    get_supabase().table("telegram_updates").update({
        "status": status, "error_type": error_type,
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }).eq("update_id", update_id).execute()


async def process_update(update: TelegramUpdate, *, claimed: bool = False) -> None:
    kind = update_kind(update)
    if kind == "ignore":
        return
    chat_id = update.message.chat.id
    if kind == "setup":
        await reply(chat_id, f"Your Telegram user ID is {chat_id}.\n\nTo enable your private library, add this number to TELEGRAM_ALLOWED_USER_IDS in the Railway backend variables and deploy. Until then, saved knowledge and Reel submission are disabled for this account.")
        return
    if not claimed and not await asyncio.to_thread(claim_update, update.update_id):
        return
    processing_tasks = BackgroundTasks()
    try:
        text = update.message.text.strip()
        parts = text.split(maxsplit=1)
        command = parts[0].split("@")[0].lower() if parts else ""
        if command in {"/start", "/help"}:
            response = HELP
        elif command == "/recent":
            response = await asyncio.to_thread(recent_items)
        elif command.startswith("/") and command != "/ask":
            response = "Unknown command.\n\n" + HELP
        else:
            match = REEL_REGEX.search(text) if command != "/ask" else None
            if match:
                payload = ReelWebhookRequest(url=match.group(0).rstrip(".,!?);]"), secret=settings.webhook_secret)
                result = await asyncio.to_thread(receive_reel, payload, processing_tasks)
                response = "Reel queued. Check the Library after processing." if result["status"] == "queued" else f"This Reel is already saved (processing status: {result.get('processing_status', 'unknown')})."
            else:
                question = parts[1].strip() if command == "/ask" and len(parts) > 1 else ("" if command == "/ask" else text)
                if not question:
                    response = "Use /ask followed by a question about your saved knowledge."
                elif len(question) > 1500:
                    response = "Please keep your question under 1,500 characters."
                else:
                    response = await asyncio.to_thread(answer_question, question)
        await reply(chat_id, response)
        # Preserve the legacy inline mode if it is explicitly selected.
        await processing_tasks()
        await asyncio.to_thread(_finish, update.update_id, "completed")
    except Exception as exc:
        # Provider and transport exceptions can contain credentials or source text.
        logger.warning("Telegram update failed update_id=%s error_type=%s", update.update_id, type(exc).__name__)
        try:
            await asyncio.to_thread(_finish, update.update_id, "failed", type(exc).__name__)
            await reply(chat_id, NO_CREDITS if isinstance(exc, AnswerCreditsError) else "I couldn't complete that request. Please try sending a new message.")
        except Exception:
            logger.warning("Telegram failure acknowledgement could not be delivered update_id=%s", update.update_id)
