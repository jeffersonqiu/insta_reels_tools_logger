"""Bounded queue processing for an ephemeral GitHub Actions runner."""

import datetime as dt
from typing import Any

from services.ingestion import canonicalize_reel_url
from services.processing import process_reel


def recover_interrupted(supabase: Any) -> int:
    """A killed runner cannot run finally. Fail old claims without paid auto-retries.

    The workflow has a 30-minute timeout; the two-hour recovery window leaves
    ample margin. Fresh in-flight processing is never reclaimed.
    """
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat()
    rows = (
        supabase.table("videos")
        .update({"status": "failed", "processing_error": "Processing was interrupted. Resubmit the Reel to retry."})
        .eq("status", "processing")
        .lt("processing_started_at", cutoff)
        .execute().data
        or []
    )
    return len(rows)


def run_queue(supabase: Any, *, limit: int = 3, video_id: str | None = None, dry_run: bool = False) -> dict:
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    recovered = 0 if dry_run else recover_interrupted(supabase)
    query = (
        supabase.table("videos").select("id,canonical_url,instagram_url")
        .eq("status", "queued").order("processed_at").order("id")
    )
    if video_id:
        query = query.eq("id", video_id)
    rows = query.limit(limit).execute().data or []
    result = {"candidates": len(rows), "recovered": recovered, "completed": 0, "failed": 0, "skipped": 0, "dry_run": dry_run}
    for row in rows:
        if dry_run:
            continue
        # Revalidate stored URLs before allowing the downloader to contact them.
        raw_url = row.get("canonical_url") or row["instagram_url"]
        try:
            url = canonicalize_reel_url(raw_url)
        except ValueError:
            supabase.table("videos").update({"status": "failed", "processing_error": "Invalid stored Instagram Reel URL."}).eq(
                "id", row["id"]
            ).eq("status", "queued").execute()
            result["failed"] += 1
            continue
        outcome = process_reel(row["id"], url)
        if "error" in outcome:
            result["failed"] += 1
        elif outcome.get("status") == "not_queued":
            result["skipped"] += 1
        else:
            result["completed"] += 1
    return result
