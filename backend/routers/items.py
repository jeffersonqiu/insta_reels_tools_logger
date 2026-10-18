from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder

from db.client import get_supabase
from services.organization import annotate_item, organize_items

router = APIRouter(prefix="/items", tags=["items"])

_NO_STORE = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}
_VIDEO_FIELDS = "id,instagram_url,caption,transcript,video_created_at,status"


@router.get("")
def list_items(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    response.headers.update(_NO_STORE)
    supabase = get_supabase()
    rows = (
        supabase.table("knowledge_items")
        .select("*")
        .order("created_at", desc=True)
        .order("id", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
        .data
        or []
    )
    return jsonable_encoder(organize_items(rows))


@router.get("/{item_id}")
def get_item(item_id: UUID, response: Response):
    response.headers.update(_NO_STORE)
    supabase = get_supabase()
    rows = supabase.table("knowledge_items").select("*").eq("id", str(item_id)).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Item not found")
    item = rows[0]
    videos = supabase.table("videos").select(_VIDEO_FIELDS).eq("id", item["video_id"]).limit(1).execute().data or []
    return jsonable_encoder({"item": annotate_item(item), "video": videos[0] if videos else None})
