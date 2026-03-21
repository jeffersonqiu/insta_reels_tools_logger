import datetime as dt
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, HTTPException, Query

from db.client import get_supabase
from models.schemas import ToolInteractionPatch

router = APIRouter(prefix="/tools", tags=["tools"])


def _reel_canonical_key(instagram_url: str) -> str:
    """
    Same Reel is often saved twice as different rows when the URL differs only by
    query string (?igsh=...) or trailing slash. Collapse those for display counts
    and Watch Reel links.
    """
    raw = (instagram_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    path = (parsed.path or "").rstrip("/").lower()
    host = (parsed.netloc or "").lower()
    scheme = (parsed.scheme or "https").lower()
    return urlunparse((scheme, host, path, "", "", ""))


@router.get("")
def list_tools(status: str = Query(default="all")):
    if status not in {"to_explore", "implemented", "not_interested", "all"}:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    supabase = get_supabase()
    tools = supabase.table("tools").select("*").order("first_seen_date", desc=True).execute().data or []
    interactions = supabase.table("user_interactions").select("*").execute().data or []
    interaction_by_tool = {row["tool_id"]: row for row in interactions}

    links = supabase.table("video_tools").select("video_id,tool_id").execute().data or []
    videos = supabase.table("videos").select("id,instagram_url").execute().data or []
    url_by_video = {v["id"]: v["instagram_url"] for v in videos}

    videos_by_tool: dict[str, list[dict]] = {}
    for link in links:
        tid = link["tool_id"]
        vid = link["video_id"]
        url = url_by_video.get(vid)
        if not url:
            continue
        key = _reel_canonical_key(url)
        if not key:
            continue
        bucket = videos_by_tool.setdefault(tid, [])
        if any(_reel_canonical_key(v["instagram_url"]) == key for v in bucket):
            continue
        bucket.append({"video_id": vid, "instagram_url": url})

    merged = []
    for t in tools:
        interaction = interaction_by_tool.get(t["id"], {})
        source_videos = videos_by_tool.get(t["id"], [])
        merged_item = {
            **t,
            "status": interaction.get("status", "to_explore"),
            "notes": interaction.get("notes"),
            "updated_at": interaction.get("updated_at"),
            "source_videos": source_videos,
            "video_count": len(source_videos),
        }
        if status == "all" or merged_item["status"] == status:
            merged.append(merged_item)
    return merged


@router.patch("/{tool_id}/interaction")
def update_interaction(tool_id: str, payload: ToolInteractionPatch):
    supabase = get_supabase()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    result = supabase.table("user_interactions").upsert(
        {
            "tool_id": tool_id,
            "status": payload.status,
            "notes": payload.notes,
            "updated_at": now,
        },
        on_conflict="tool_id",
    ).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tool interaction update failed")
    return result.data[0]
