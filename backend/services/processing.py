import datetime as dt
import logging
from typing import Any

from db.client import get_supabase
from models.schemas import ToolExtraction
from services.deduplicator import upsert_tools
from services.downloader import download_reel_audio
from services.extractor import extract_tools_from_transcript
from services.transcriber import transcribe_audio_file

logger = logging.getLogger(__name__)


def _record_processing_error(supabase: Any, video_id: str, message: str) -> None:
    try:
        supabase.table("videos").update({"processing_error": message[:4000]}).eq("id", video_id).execute()
    except Exception:
        logger.exception("Failed to write processing_error for video %s", video_id)


def process_reel(url: str) -> dict[str, Any]:
    supabase = get_supabase()
    video_id: str | None = None
    try:
        audio_path, video_date, caption = download_reel_audio(url)
        insert_result = supabase.table("videos").insert(
            {
                "instagram_url": url,
                "video_created_at": video_date.isoformat() if video_date else None,
                "caption": caption,
            }
        ).execute()
        video_id = insert_result.data[0]["id"]

        transcript = transcribe_audio_file(audio_path)
        supabase.table("videos").update({"transcript": transcript}).eq("id", video_id).execute()

        tools: list[ToolExtraction] = extract_tools_from_transcript(transcript, caption=caption)
        raw_extraction = [t.model_dump() for t in tools]
        supabase.table("videos").update({"raw_extraction": raw_extraction}).eq("id", video_id).execute()

        tool_ids = upsert_tools(tools, video_id, video_date or dt.date.today())
        logger.info("Processed reel %s -> %s tools", url, len(tool_ids))
        return {"video_id": video_id, "tool_ids": tool_ids}
    except Exception as exc:
        logger.exception("process_reel failed for %s", url)
        if video_id:
            _record_processing_error(supabase, video_id, f"{type(exc).__name__}: {exc}")
        raise
