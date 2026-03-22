import datetime as dt
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder

from db.client import get_supabase
from models.schemas import ToolInteractionPatch

router = APIRouter(prefix="/tools", tags=["tools"])

_NO_STORE = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}


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


def _build_merged_tools() -> list[dict]:
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
        merged.append(
            {
                **t,
                "status": interaction.get("status", "to_explore"),
                "notes": interaction.get("notes"),
                "updated_at": interaction.get("updated_at"),
                "source_videos": source_videos,
                "video_count": len(source_videos),
            }
        )
    return merged


def _apply_cache_headers(response: Response) -> None:
    for k, v in _NO_STORE.items():
        response.headers[k] = v


@router.get("/counts")
def tool_status_counts(response: Response):
    """Tab badge counts across all tools (not filtered by current tab)."""
    _apply_cache_headers(response)
    merged = _build_merged_tools()
    counts = {"all": len(merged), "to_explore": 0, "implemented": 0, "not_interested": 0}
    for m in merged:
        s = m.get("status") or "to_explore"
        if s in ("to_explore", "implemented", "not_interested"):
            counts[s] += 1
    return counts


@router.get("/tags")
def list_all_tags(response: Response):
    """Distinct tags from all tools for filter UI."""
    _apply_cache_headers(response)
    supabase = get_supabase()
    rows = supabase.table("tools").select("tags").execute().data or []
    seen: set[str] = set()
    for row in rows:
        for tag in row.get("tags") or []:
            if tag and isinstance(tag, str) and tag.strip():
                seen.add(tag.strip())
    return sorted(seen, key=str.lower)


@router.get("")
def list_tools(response: Response, status: str = Query(default="all")):
    if status not in {"to_explore", "implemented", "not_interested", "all"}:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    _apply_cache_headers(response)

    merged = _build_merged_tools()
    if status == "all":
        filtered = merged
    else:
        filtered = [m for m in merged if m["status"] == status]
    # Supabase returns UUID/datetime objects; JSONResponse must not 500 on encode.
    return jsonable_encoder(filtered)


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
    return jsonable_encoder(result.data[0])
