"""Telegram transport and a derived webhook secret; never log credential URLs."""

import hashlib
import hmac
import logging
import re
from urllib.parse import quote

import httpx

from config import settings


class TelegramError(Exception):
    pass


class _RedactBotToken(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # Redact the URL credential segment, including percent-encoded malformed
        # values. Matching only the raw configured value misses URL encoding.
        message = re.sub(r'(https?://api\.telegram\.org/bot)[^/\s"\']+', r'\1[redacted]', message, flags=re.IGNORECASE)
        token = settings.telegram_bot_token
        if token:
            for representation in {token, quote(token, safe=""), quote(token, safe=":")}:
                message = message.replace(representation, "[redacted]")
        record.msg, record.args = message, ()
        return True


# httpx normally logs request URLs at INFO, including Telegram's URL token.
logging.getLogger("httpx").addFilter(_RedactBotToken())
logging.getLogger("httpcore").addFilter(_RedactBotToken())


def webhook_token() -> str:
    if not settings.webhook_secret:
        return ""
    return hmac.new(settings.webhook_secret.encode(), b"telegram-webhook-v1", hashlib.sha256).hexdigest()


async def bot_request(method: str, payload: dict | None = None):
    if not settings.telegram_bot_token:
        raise TelegramError("Telegram bot is not configured.")
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", settings.telegram_bot_token):
        raise TelegramError("Telegram token format is invalid. Copy only the BotFather token without spaces.")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}", json=payload or {},
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise TelegramError("Telegram request failed.")
            return data["result"]
    except httpx.HTTPStatusError as exc:
        raise TelegramError(f"Telegram returned HTTP {exc.response.status_code}. Check the bot token.") from None
    except TelegramError:
        raise
    except Exception:
        # Exception strings and HTTP request objects may contain the bot token.
        raise TelegramError("Telegram request failed. Check the bot configuration.") from None


async def reply(chat_id: int, text: str) -> None:
    while text:
        # Telegram's length limit uses UTF-16 units, including two for emoji.
        chunk = text.encode("utf-16-le")[:8000].decode("utf-16-le", errors="ignore")
        if len(chunk) < len(text):
            boundary = chunk.rfind("\n")
            if boundary > len(chunk) // 2:
                chunk = chunk[:boundary + 1]
        await bot_request("sendMessage", {
            "chat_id": chat_id, "text": chunk, "link_preview_options": {"is_disabled": True},
        })
        text = text[len(chunk):]
