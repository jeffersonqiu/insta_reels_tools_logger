import datetime as dt
import logging
from typing import Any

from db.client import get_supabase
from services.deduplicator import upsert_tools
from services.downloader import cleanup_reel_audio, download_reel_audio
from services.extractor import extract_knowledge
from services.knowledge import upsert_knowledge_item
from services.transcriber import transcribe_audio_file

logger = logging.getLogger(__name__)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _mark_failed(supabase: Any, video_id: str, message: str) -> None:
    try:
        supabase.table("videos").update(
            {"status": "failed", "processing_error": message[:4000]}
        ).eq("id", video_id).execute()
    except Exception:
        logger.exception("Failed to mark video_id=%s as failed", video_id)


def process_reel(video_id: str, canonical_url: str) -> dict[str, Any]:
    """Process an already-persisted `videos` row: queued -> processing -> completed | failed."""
    supabase = get_supabase()
    claimed = False
    audio_path = None
    try:
        row = supabase.table("videos").select("attempt_count,status").eq("id", video_id).limit(1).execute().data
        if not row or row[0].get("status") != "queued":
            return {"video_id": video_id, "status": "not_queued"}
        attempts = (row[0].get("attempt_count") or 0) + 1
        # Only one caller can claim this particular queued attempt, including
        # during the transition from Railway background tasks to Actions.
        claimed_rows = supabase.table("videos").update(
            {
                "status": "processing",
                "attempt_count": attempts,
                "processing_started_at": _now(),
                "processing_error": None,
                "completed_at": None,
            }
        ).eq("id", video_id).eq("status", "queued").eq("attempt_count", attempts - 1).execute().data
        if not claimed_rows:
            return {"video_id": video_id, "status": "not_queued"}
        claimed = True
        logger.info("video_id=%s canonical_url=%s state=processing attempt=%s", video_id, canonical_url, attempts)

        audio_path, video_date, caption = download_reel_audio(canonical_url)
        supabase.table("videos").update(
            {"video_created_at": video_date.isoformat() if video_date else None, "caption": caption}
        ).eq("id", video_id).execute()

        transcript = transcribe_audio_file(audio_path)
        supabase.table("videos").update({"transcript": transcript}).eq("id", video_id).execute()

        knowledge = extract_knowledge(transcript, caption=caption)
        # videos.raw_extraction keeps its legacy shape (tool list); the full payload lives on knowledge_items.
        raw_tools = [t.model_dump() for t in knowledge.tools]
        supabase.table("videos").update({"raw_extraction": raw_tools}).eq("id", video_id).execute()

        item_id = upsert_knowledge_item(supabase, video_id, canonical_url, knowledge)
        logger.info("video_id=%s knowledge_item_id=%s saved", video_id, item_id)

        tool_ids = upsert_tools(knowledge.tools, video_id, video_date or dt.date.today())

        supabase.table("videos").update(
            {"status": "completed", "completed_at": _now(), "processing_error": None}
        ).eq("id", video_id).execute()
        logger.info(
            "video_id=%s canonical_url=%s state=completed tools=%s", video_id, canonical_url, len(tool_ids)
        )
        return {"video_id": video_id, "tool_ids": tool_ids}
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.exception(
            "video_id=%s canonical_url=%s state=failed failure_type=%s", video_id, canonical_url, type(exc).__name__
        )
        if claimed:
            _mark_failed(supabase, video_id, msg)
        # Do not re-raise: BackgroundTasks would log "Exception in ASGI application"
        # for expected failures (e.g. Instagram rate limits / yt-dlp download errors).
        return {"error": msg, "video_id": video_id}
    finally:
        if audio_path:
            cleanup_reel_audio(audio_path)
