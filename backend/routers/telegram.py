import asyncio
import hmac
import logging
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, HttpUrl, ValidationError

from config import settings
from services.telegram_api import TelegramError, bot_request, webhook_token
from services.telegram_handler import TelegramUpdate, claim_update, process_update, update_kind

router = APIRouter(tags=["telegram"])
logger = logging.getLogger(__name__)


@router.post("/webhook/telegram")
async def receive_telegram(
    request: Request, background_tasks: BackgroundTasks,
    telegram_secret: str = Header(default="", alias="X-Telegram-Bot-Api-Secret-Token"),
):
    expected = webhook_token()
    if not expected or not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram is not configured")
    if not hmac.compare_digest(telegram_secret.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
    body = await request.body()
    if len(body) > 131072:
        raise HTTPException(status_code=413, detail="Update is too large")
    try:
        update = TelegramUpdate.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid Telegram update") from None
    kind = update_kind(update)
    if kind == "ignore":
        return {"status": "ignored"}
    if kind == "process":
        try:
            claimed = await asyncio.to_thread(claim_update, update.update_id)
        except Exception as exc:
            logger.warning("Telegram update claim failed error_type=%s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Telegram update storage is unavailable") from None
        if not claimed:
            return {"status": "duplicate"}
    background_tasks.add_task(process_update, update, claimed=kind == "process")
    return {"status": "accepted"}


class TelegramSetup(BaseModel):
    secret: str
    expected_username: str
    operation: Literal["inspect", "register"] = "inspect"
    public_api_url: HttpUrl | None = None


@router.post("/telegram/setup")
async def setup_telegram(payload: TelegramSetup):
    # Reuse the existing administrator secret; the bot token stays on Railway.
    if not settings.webhook_secret or not hmac.compare_digest(payload.secret.encode(), settings.webhook_secret.encode()):
        raise HTTPException(status_code=401, detail="Invalid secret")
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN is missing")
    target_url = None
    if payload.operation == "register":
        parsed = urlsplit(str(payload.public_api_url or ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise HTTPException(status_code=400, detail="Use the HTTPS API origin without a path or credentials")
        target_url = str(payload.public_api_url).rstrip("/") + "/api/webhook/telegram"
    try:
        bot = await bot_request("getMe")
        if str(bot.get("username", "")).casefold() != payload.expected_username.lstrip("@").casefold():
            raise HTTPException(status_code=400, detail="Configured token belongs to a different bot")
        if target_url:
            await bot_request("setWebhook", {
                "url": target_url, "secret_token": webhook_token(),
                "allowed_updates": ["message"], "max_connections": 1,
            })
        info = await bot_request("getWebhookInfo")
    except TelegramError:
        raise HTTPException(status_code=503, detail="Telegram request failed; check the bot token") from None
    return {
        "username": bot["username"], "webhook_configured": bool(info.get("url")),
        "registered_expected_url": bool(target_url and info.get("url") == target_url),
        "pending_update_count": info.get("pending_update_count", 0),
        "webhook_has_error": bool(info.get("last_error_message")),
        "allowed_user_count": len([value for value in settings.telegram_allowed_user_ids.split(",") if value]),
    }
