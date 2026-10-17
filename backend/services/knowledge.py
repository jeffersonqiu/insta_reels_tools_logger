"""Persistence for `knowledge_items` (one row per video, upserted on video_id)."""

import datetime as dt
from typing import Any

from models.schemas import KnowledgeExtraction


def upsert_knowledge_item(supabase: Any, video_id: str, source_url: str, extraction: KnowledgeExtraction) -> str:
    """Create or update the knowledge item for a video; retries reuse the same row. Returns its id."""
    dumped = extraction.model_dump()
    row = {
        "video_id": video_id,
        "source_type": "instagram_reel",
        "source_url": source_url,
        "title": extraction.title,
        "summary": extraction.summary,
        "key_ideas": dumped["key_ideas"],
        "repositories": dumped["repositories"],
        "concepts": dumped["concepts"],
        "action_items": dumped["action_items"],
        "tags": extraction.tags,
        "raw_extraction": dumped,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    result = supabase.table("knowledge_items").upsert(row, on_conflict="video_id").execute()
    return result.data[0]["id"]
