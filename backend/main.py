import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.diagnostics import router as diagnostics_router
from routers.metrics import router as metrics_router
from routers.tools import router as tools_router
from routers.videos import router as videos_router
from routers.webhook import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

app = FastAPI(title="AI Tools Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnostics_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(videos_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
