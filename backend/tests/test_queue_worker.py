"""Queue-only ingestion, exclusive claims, bounded batches and interrupted jobs."""

import datetime as dt
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from main import app
from models.schemas import KnowledgeExtraction
from scripts import process_queue
from services import deduplicator, processing, queue_worker
from test_knowledge_items import FakeSupabase, _Q, _R


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    now = dt.datetime.now(dt.timezone.utc)
    fake.tables["videos"] = [
        {"id": "new", "instagram_url": "https://www.instagram.com/reel/NEW/", "status": "queued", "attempt_count": 0,
         "processed_at": (now - dt.timedelta(minutes=1)).isoformat()},
        {"id": "old", "instagram_url": "https://www.instagram.com/reel/OLD/", "status": "queued", "attempt_count": 0,
         "processed_at": (now - dt.timedelta(minutes=2)).isoformat()},
        {"id": "failed", "status": "failed", "attempt_count": 1},
        {"id": "stale", "status": "processing", "processing_started_at": (now - dt.timedelta(hours=3)).isoformat()},
        {"id": "fresh", "status": "processing", "processing_started_at": (now - dt.timedelta(minutes=10)).isoformat()},
    ]
    monkeypatch.setattr(processing, "get_supabase", lambda: fake)
    monkeypatch.setattr(deduplicator, "get_supabase", lambda: fake)
    return fake


def test_queue_mode_persists_without_background_processing(monkeypatch):
    db = FakeSupabase()
    monkeypatch.setattr("routers.webhook.get_supabase", lambda: db)
    monkeypatch.setattr("routers.webhook.settings.webhook_secret", "test-secret")
    monkeypatch.setattr("routers.webhook.settings.processing_mode", "github_actions")
    monkeypatch.setattr("routers.webhook.process_reel", lambda *a: pytest.fail("Actions mode must only enqueue"))
    client = TestClient(app)
    request = {"url": "https://instagram.com/reel/A/?igsh=one", "secret": "test-secret"}
    first = client.post("/api/webhook/reel", json=request)
    assert first.status_code == 200 and first.json()["status"] == "queued"
    assert len(db.tables["videos"]) == 1
    second = client.post("/api/webhook/reel", json={**request, "url": "https://instagram.com/reel/A/?igsh=two"})
    assert second.json()["status"] == "already_exists"
    assert second.json()["video_id"] == first.json()["video_id"]
    db.tables["videos"][0]["status"] = "failed"
    assert client.post("/api/webhook/reel", json=request).json()["status"] == "queued"
    assert len(db.tables["videos"]) == 1


def test_mode_validated_and_defaults_to_inline():
    assert Settings(_env_file=None).processing_mode == "inline"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, processing_mode="typo")


@pytest.mark.parametrize("mode", ["inline", "github_actions"])
def test_deployed_processing_mode_can_be_verified_without_credentials(monkeypatch, mode):
    monkeypatch.setattr("routers.diagnostics.settings.processing_mode", mode)
    response = TestClient(app).get("/api/diagnostics/processing")
    assert response.status_code == 200 and response.json() == {"mode": mode}


def test_dry_run_never_recovers_or_processes(db, monkeypatch):
    before = deepcopy(db.tables)
    monkeypatch.setattr(queue_worker, "process_reel", lambda *a: pytest.fail("No paid processing in dry run"))
    result = queue_worker.run_queue(db, dry_run=True)
    assert result["candidates"] == 2 and result["dry_run"] is True
    assert db.tables == before


def test_batch_is_oldest_first_and_does_not_retry_failed(db, monkeypatch):
    seen = []
    monkeypatch.setattr(queue_worker, "process_reel", lambda vid, url: seen.append((vid, url)) or {"video_id": vid})
    result = queue_worker.run_queue(db, limit=1)
    assert seen == [("old", "https://www.instagram.com/reel/OLD/")]
    assert result["completed"] == 1 and result["recovered"] == 1
    assert next(r for r in db.tables["videos"] if r["id"] == "stale")["status"] == "failed"
    assert next(r for r in db.tables["videos"] if r["id"] == "fresh")["status"] == "processing"


def test_specific_queued_video_can_be_selected(db, monkeypatch):
    seen = []
    monkeypatch.setattr(queue_worker, "process_reel", lambda vid, url: seen.append(vid) or {"video_id": vid})
    result = queue_worker.run_queue(db, video_id="new")
    assert seen == ["new"] and result["candidates"] == 1


def test_failure_does_not_prevent_next_video(db, monkeypatch):
    monkeypatch.setattr(queue_worker, "process_reel", lambda vid, url: {"error": "failed"} if vid == "old" else {"video_id": vid})
    result = queue_worker.run_queue(db)
    assert result["failed"] == result["completed"] == 1


def test_invalid_stored_url_is_not_downloaded(db, monkeypatch):
    db.tables["videos"][1]["instagram_url"] = "http://127.0.0.1/internal"
    monkeypatch.setattr(queue_worker, "process_reel", lambda *a: pytest.fail("Invalid URL must never reach downloader"))
    result = queue_worker.run_queue(db, limit=1)
    assert result["failed"] == 1
    assert db.tables["videos"][1]["status"] == "failed"


def test_completed_or_processing_video_cannot_be_claimed_again(db, monkeypatch):
    monkeypatch.setattr(processing, "download_reel_audio", lambda *a: pytest.fail("Duplicate claim must not download"))
    before = deepcopy(db.tables)
    assert processing.process_reel("fresh", "u")["status"] == "not_queued"
    assert processing.process_reel("failed", "u")["status"] == "not_queued"
    assert processing.process_reel("missing", "u")["status"] == "not_queued"
    assert db.tables == before


def test_lost_claim_race_does_not_download_or_mark_other_worker_failed(db, monkeypatch):
    original = _Q.execute

    def execute(query):
        if query.op == "update" and query.payload.get("status") == "processing":
            db.tables["videos"][1].update(status="processing", attempt_count=1)
            return _R([])
        return original(query)

    monkeypatch.setattr(_Q, "execute", execute)
    monkeypatch.setattr(processing, "download_reel_audio", lambda *a: pytest.fail("Only winner may download"))
    assert processing.process_reel("old", "u")["status"] == "not_queued"
    assert db.tables["videos"][1]["status"] == "processing"


def test_worker_runs_the_existing_knowledge_pipeline(db, monkeypatch):
    monkeypatch.setattr(processing, "download_reel_audio", lambda *a: ("/tmp/stub-audio.m4a", None, "caption"))
    monkeypatch.setattr(processing, "transcribe_audio_file", lambda *a: "transcript")
    monkeypatch.setattr(processing, "extract_knowledge", lambda *a, **kw: KnowledgeExtraction(title="T", summary="S"))
    result = queue_worker.run_queue(db, video_id="old")
    assert result["completed"] == 1
    assert db.tables["videos"][1]["status"] == "completed"
    assert db.tables["videos"][1]["attempt_count"] == 1
    assert db.tables["knowledge_items"][0]["video_id"] == "old"
    assert queue_worker.run_queue(db, video_id="old")["candidates"] == 0


@pytest.mark.parametrize("limit", [0, -1, 11])
def test_worker_rejects_invalid_batch_size(db, limit):
    before = deepcopy(db.tables)
    with pytest.raises(ValueError):
        queue_worker.run_queue(db, limit=limit)
    assert db.tables == before


@pytest.mark.parametrize("argv", [["--limit", "0"], ["--limit", "11"], ["--video-id", "not-uuid"]])
def test_cli_rejects_invalid_input_before_database(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["process_queue.py", *argv])
    monkeypatch.setattr(process_queue, "get_supabase", lambda: pytest.fail("Invalid input must not query database"))
    with pytest.raises(SystemExit) as error:
        process_queue.main()
    assert error.value.code == 2
