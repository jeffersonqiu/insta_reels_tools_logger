import datetime as dt

from fastapi import APIRouter, HTTPException, Query

from db.client import get_supabase
from models.schemas import ToolInteractionPatch

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
def list_tools(status: str = Query(default="all")):
    if status not in {"to_explore", "implemented", "not_interested", "all"}:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    supabase = get_supabase()
    tools = supabase.table("tools").select("*").order("first_seen_date", desc=True).execute().data or []
    interactions = supabase.table("user_interactions").select("*").execute().data or []
    interaction_by_tool = {row["tool_id"]: row for row in interactions}

    merged = []
    for t in tools:
        interaction = interaction_by_tool.get(t["id"], {})
        merged_item = {
            **t,
            "status": interaction.get("status", "to_explore"),
            "notes": interaction.get("notes"),
            "updated_at": interaction.get("updated_at"),
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
