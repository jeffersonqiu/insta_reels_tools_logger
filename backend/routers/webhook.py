import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from config import settings
from db.client import get_supabase
from models.schemas import ReelWebhookRequest
from services.ingestion import InvalidReelUrl, canonicalize_reel_url, create_or_get_video, requeue_failed
from services.processing import process_reel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/reel")
def receive_reel(payload: ReelWebhookRequest, background_tasks: BackgroundTasks):
    if payload.secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")

    try:
        canonical_url = canonicalize_reel_url(str(payload.url))
    except InvalidReelUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    supabase = get_supabase()
    video, created = create_or_get_video(supabase, canonical_url)
    video_id = video["id"]

    if created:
        logger.info("Reel accepted video_id=%s canonical_url=%s status=queued", video_id, canonical_url)
    elif video["status"] == "failed" and requeue_failed(supabase, video_id):
        # A previously failed Reel is retried on resubmission (the old flow left no row, so retry was implicit).
        logger.info("Reel requeued video_id=%s canonical_url=%s status=failed->queued", video_id, canonical_url)
    else:
        return {"status": "already_exists", "video_id": video_id, "processing_status": video["status"]}

    background_tasks.add_task(process_reel, video_id, canonical_url)
    return {"status": "queued", "video_id": video_id}
