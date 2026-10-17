from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder

from db.client import get_supabase

router = APIRouter(prefix="/items", tags=["items"])

_NO_STORE = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}
_VIDEO_FIELDS = "id,instagram_url,caption,transcript,video_created_at,status"


@router.get("")
def list_items(response: Response, limit: int = Query(50, ge=1, le=200)):
    response.headers.update(_NO_STORE)
    supabase = get_supabase()
    rows = (
        supabase.table("knowledge_items")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    return jsonable_encoder(rows)


@router.get("/{item_id}")
def get_item(item_id: str, response: Response):
    response.headers.update(_NO_STORE)
    supabase = get_supabase()
    rows = supabase.table("knowledge_items").select("*").eq("id", item_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Item not found")
    item = rows[0]
    videos = supabase.table("videos").select(_VIDEO_FIELDS).eq("id", item["video_id"]).limit(1).execute().data or []
    return jsonable_encoder({"item": item, "video": videos[0] if videos else None})
