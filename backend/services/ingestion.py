"""Durable ingestion helpers: canonical Reel URLs and the queued `videos` row."""

import logging
import re
from typing import Any
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
# Optional leading username segment (instagram.com/<user>/reel/<code>); shortcodes are case-sensitive.
_PATH_RE = re.compile(r"^/(?:[^/]+/)?(?:reels?|p)/([A-Za-z0-9_-]+)/?$")

_COLUMNS = "id, status, canonical_url, instagram_url"


class InvalidReelUrl(ValueError):
    pass


def canonicalize_reel_url(url: str) -> str:
    """https://www.instagram.com/reel/<shortcode>/ — query, fragment and host variants stripped."""
    try:
        parts = urlsplit(url.strip())
    except ValueError as exc:
        raise InvalidReelUrl("Not a valid URL") from exc
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or host not in _HOSTS:
        raise InvalidReelUrl("Not an Instagram URL")
    match = _PATH_RE.match(parts.path)
    if not match:
        raise InvalidReelUrl("Not an Instagram Reel URL")
    return f"https://www.instagram.com/reel/{match.group(1)}/"


def _is_unique_violation(exc: Exception) -> bool:
    return getattr(exc, "code", None) == "23505" or "23505" in str(exc) or "duplicate key" in str(exc).lower()


def find_video(supabase: Any, canonical_url: str) -> dict | None:
    # canonical_url covers new/backfilled rows; instagram_url covers legacy rows whose
    # stored URL already happens to be canonical.
    for column in ("canonical_url", "instagram_url"):
        rows = supabase.table("videos").select(_COLUMNS).eq(column, canonical_url).limit(1).execute().data
        if rows:
            return rows[0]
    return None


def create_or_get_video(supabase: Any, canonical_url: str) -> tuple[dict, bool]:
    """Return (video_row, created). Race-safe via the unique index on canonical_url."""
    existing = find_video(supabase, canonical_url)
    if existing:
        return existing, False
    try:
        inserted = (
            supabase.table("videos")
            .insert({"instagram_url": canonical_url, "canonical_url": canonical_url, "status": "queued"})
            .execute()
            .data
        )
        return inserted[0], True
    except Exception as exc:
        if not _is_unique_violation(exc):
            raise
        existing = find_video(supabase, canonical_url)
        if existing is None:
            raise
        return existing, False


def requeue_failed(supabase: Any, video_id: str) -> bool:
    """failed -> queued. Conditional update so only one concurrent request wins the retry."""
    rows = (
        supabase.table("videos")
        .update({"status": "queued"})
        .eq("id", video_id)
        .eq("status", "failed")
        .execute()
        .data
    )
    return bool(rows)
