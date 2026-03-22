"""
Dashboard metrics: 7-day ingestion, tag prevalence, status mix, daily series.
"""

from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Response

from db.client import get_supabase
from routers.tools import _build_merged_tools

router = APIRouter(prefix="/metrics", tags=["metrics"])

_NO_STORE = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_processed_at(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        s = raw.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


@router.get("/overview")
def metrics_overview(response: Response):
    """Single payload for dashboard: KPIs, tags, status, 7-day series."""
    for k, v in _NO_STORE.items():
        response.headers[k] = v

    supabase = get_supabase()
    now = _utc_now()
    cutoff = now - timedelta(days=7)
    cutoff_date = cutoff.date()

    videos_rows = supabase.table("videos").select("id,processed_at").execute().data or []

    video_ids_last_7d: set[str] = set()
    for row in videos_rows:
        ts = _parse_processed_at(row.get("processed_at"))
        if ts and ts >= cutoff:
            video_ids_last_7d.add(row["id"])

    videos_last_7d = len(video_ids_last_7d)

    links = supabase.table("video_tools").select("video_id,tool_id").execute().data or []
    tool_mentions_last_7d = sum(1 for row in links if row.get("video_id") in video_ids_last_7d)

    distinct_tools_in_new_reels = len({row["tool_id"] for row in links if row.get("video_id") in video_ids_last_7d})

    today_utc = _utc_now().date()
    tools_rows = supabase.table("tools").select("id,first_seen_date,tags").execute().data or []

    tools_first_seen_last_7d = 0
    tag_counts: Counter[str] = Counter()
    for t in tools_rows:
        fsd = t.get("first_seen_date")
        if fsd:
            if isinstance(fsd, str):
                try:
                    fsd_d = date.fromisoformat(fsd[:10])
                except ValueError:
                    fsd_d = None
            elif isinstance(fsd, date):
                fsd_d = fsd
            else:
                fsd_d = None
            # Same rolling horizon as reels (cutoff.date()), not a separate calendar window.
            if fsd_d and fsd_d >= cutoff_date:
                tools_first_seen_last_7d += 1
        for tag in t.get("tags") or []:
            if tag and isinstance(tag, str) and tag.strip():
                tag_counts[tag.strip()] += 1

    top_tags = [{"tag": tag, "count": c} for tag, c in tag_counts.most_common(15)]

    merged = _build_merged_tools()
    status_breakdown = {"all": len(merged), "to_explore": 0, "implemented": 0, "not_interested": 0}
    for m in merged:
        s = m.get("status") or "to_explore"
        if s in ("to_explore", "implemented", "not_interested"):
            status_breakdown[s] += 1

    implemented_pct = (
        round(100.0 * status_breakdown["implemented"] / status_breakdown["all"], 1) if status_breakdown["all"] else 0.0
    )

    # Last 7 calendar days (inclusive), UTC date buckets
    day_start = today_utc - timedelta(days=6)
    day_keys = [(day_start + timedelta(days=i)).isoformat() for i in range(7)]
    per_day_videos: dict[str, set[str]] = {k: set() for k in day_keys}
    for row in videos_rows:
        ts = _parse_processed_at(row.get("processed_at"))
        if not ts:
            continue
        d_key = ts.date().isoformat()
        if d_key in per_day_videos:
            per_day_videos[d_key].add(row["id"])

    video_to_tools: dict[str, set[str]] = {}
    for row in links:
        vid = row.get("video_id")
        tid = row.get("tool_id")
        if not vid or not tid:
            continue
        video_to_tools.setdefault(vid, set()).add(tid)

    series_last_7d = []
    for d_key in day_keys:
        vids = per_day_videos[d_key]
        tools_linked: set[str] = set()
        for vid in vids:
            tools_linked.update(video_to_tools.get(vid, set()))
        series_last_7d.append(
            {
                "date": d_key,
                "videos_processed": len(vids),
                "distinct_tools_linked": len(tools_linked),
            }
        )

    return {
        "videos_last_7d": videos_last_7d,
        "tool_mentions_last_7d": tool_mentions_last_7d,
        "distinct_tools_in_new_reels_7d": distinct_tools_in_new_reels,
        "tools_first_seen_last_7d": tools_first_seen_last_7d,
        "tag_prevalence": top_tags,
        "status_breakdown": status_breakdown,
        "implemented_pct": implemented_pct,
        "series_last_7d": series_last_7d,
    }
