import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db.client import get_supabase
from routers.diagnostics import router as diagnostics_router
from routers.items import router as items_router
from routers.metrics import router as metrics_router
from routers.tools import router as tools_router
from routers.telegram import router as telegram_router
from routers.videos import router as videos_router
from routers.webhook import router as webhook_router

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

app = FastAPI(title="AI Tools Tracker API")

# Browsers reject allow_origins=["*"] with allow_credentials=True; keep credentials off
# for this API (axios default) so any static host (e.g. Vercel) can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnostics_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(videos_router, prefix="/api")
app.include_router(items_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        supabase = get_supabase()
        supabase.table("videos").select("id").limit(1).execute()
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="database unavailable") from None
    return {"status": "ok", "database": "ok"}
