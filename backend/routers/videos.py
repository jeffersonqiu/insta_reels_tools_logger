from fastapi import APIRouter, HTTPException

from db.client import get_supabase

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("")
def list_videos():
    supabase = get_supabase()
    videos = (
        supabase.table("videos")
        .select("*")
        .order("video_created_at", desc=True)
        .execute()
        .data
        or []
    )
    links = supabase.table("video_tools").select("*").execute().data or []
    tools = supabase.table("tools").select("id,name").execute().data or []
    tool_name_by_id = {t["id"]: t["name"] for t in tools}

    for video in videos:
        related = [row["tool_id"] for row in links if row["video_id"] == video["id"]]
        video["tool_names"] = [tool_name_by_id[tid] for tid in related if tid in tool_name_by_id]
    return videos


@router.get("/{video_id}")
def get_video(video_id: str):
    supabase = get_supabase()
    video_rows = supabase.table("videos").select("*").eq("id", video_id).limit(1).execute().data or []
    if not video_rows:
        raise HTTPException(status_code=404, detail="Video not found")
    video = video_rows[0]

    links = supabase.table("video_tools").select("*").eq("video_id", video_id).execute().data or []
    tool_ids = [row["tool_id"] for row in links]
    tools = []
    if tool_ids:
        tools = supabase.table("tools").select("*").in_("id", tool_ids).execute().data or []

    interactions = supabase.table("user_interactions").select("*").in_("tool_id", tool_ids).execute().data or []
    interaction_by_tool = {row["tool_id"]: row for row in interactions}

    merged_tools = []
    for tool in tools:
        interaction = interaction_by_tool.get(tool["id"], {})
        merged_tools.append(
            {
                **tool,
                "status": interaction.get("status", "to_explore"),
                "notes": interaction.get("notes"),
                "updated_at": interaction.get("updated_at"),
            }
        )

    video["tools"] = merged_tools
    return video
