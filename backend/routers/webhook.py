from fastapi import APIRouter, BackgroundTasks, HTTPException

from config import settings
from db.client import get_supabase
from models.schemas import ReelWebhookRequest
from services.processing import process_reel

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/reel")
def receive_reel(payload: ReelWebhookRequest, background_tasks: BackgroundTasks):
    if payload.secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")

    supabase = get_supabase()
    existing = (
        supabase.table("videos")
        .select("id")
        .eq("instagram_url", str(payload.url))
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return {"status": "already_processed"}

    background_tasks.add_task(process_reel, str(payload.url))
    return {"status": "processing"}
