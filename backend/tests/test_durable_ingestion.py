"""Durable ingestion: canonical URLs, queued row before processing, state lifecycle. No network."""

import datetime as dt
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from services import ingestion, processing
from services.ingestion import InvalidReelUrl, canonicalize_reel_url


class FakeSupabase:
    """Minimal in-memory stand-in for the supabase-py query builder (videos table only)."""

    def __init__(self):
        self.rows: list[dict] = []
        self.history: list[tuple[str, str]] = []  # (video_id, status) transitions

    def table(self, name):
        assert name == "videos"
        return _Query(self)


class _Query:
    def __init__(self, db):
        self.db, self.op, self.payload, self.filters = db, "select", None, []

    def select(self, *_):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def limit(self, *_):
        return self

    def _match(self):
        return [r for r in self.db.rows if all(r.get(c) == v for c, v in self.filters)]

    def execute(self):
        db = self.db
        if self.op == "insert":
            url = self.payload.get("canonical_url")
            if url and any(r.get("canonical_url") == url for r in db.rows):
                raise Exception("duplicate key value violates unique constraint (23505)")
            row = {"id": str(uuid.uuid4()), "status": "queued", "attempt_count": 0, "canonical_url": None, **self.payload}
            db.rows.append(row)
            db.history.append((row["id"], row["status"]))
            return _Result([dict(row)])
        if self.op == "update":
            matched = self._match()
            for r in matched:
                r.update(self.payload)
                if "status" in self.payload:
                    db.history.append((r["id"], self.payload["status"]))
            return _Result([dict(r) for r in matched])
        return _Result([dict(r) for r in self._match()])


class _Result:
    def __init__(self, data):
        self.data = data


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr("routers.webhook.get_supabase", lambda: fake)
    monkeypatch.setattr("services.processing.get_supabase", lambda: fake)
    monkeypatch.setattr("routers.webhook.settings.webhook_secret", "s3cret")
    return fake


@pytest.fixture
def scheduled(monkeypatch):
    calls = []
    monkeypatch.setattr("routers.webhook.process_reel", lambda *a: calls.append(a))
    return calls


def _post(url="https://www.instagram.com/reel/ABC123/", secret="s3cret"):
    return TestClient(app).post("/api/webhook/reel", json={"url": url, "secret": secret})


# --- canonicalization -------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/reel/ABC123/",
        "https://www.instagram.com/reel/ABC123/?igsh=xxxx",
        "https://instagram.com/reel/ABC123?utm_source=foo",
        "http://m.instagram.com/reel/ABC123/#frag",
        "https://www.instagram.com/someuser/reel/ABC123/?igsh=1",
        "https://www.instagram.com/reels/ABC123",
    ],
)
def test_canonicalization_variants(url):
    assert canonicalize_reel_url(url) == "https://www.instagram.com/reel/ABC123/"


def test_shortcode_case_preserved():
    assert canonicalize_reel_url("https://instagram.com/reel/AbC_d-Ef9?x=1") == "https://www.instagram.com/reel/AbC_d-Ef9/"
    assert canonicalize_reel_url("https://instagram.com/reel/abc") != canonicalize_reel_url("https://instagram.com/reel/ABC")


@pytest.mark.parametrize("url", ["https://example.com/reel/ABC/", "https://www.instagram.com/", "ftp://instagram.com/reel/A/"])
def test_canonicalization_rejects(url):
    with pytest.raises(InvalidReelUrl):
        canonicalize_reel_url(url)


# --- webhook ---------------------------------------------------------------

def test_first_submission_creates_queued_row_before_processing(db, scheduled):
    r = _post("https://instagram.com/reel/ABC123?utm_source=foo")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert len(db.rows) == 1
    row = db.rows[0]
    assert body["video_id"] == row["id"]
    assert row["status"] == "queued"
    assert row["canonical_url"] == row["instagram_url"] == "https://www.instagram.com/reel/ABC123/"
    assert scheduled == [(row["id"], "https://www.instagram.com/reel/ABC123/")]


def test_duplicate_canonical_url_creates_no_second_row(db, scheduled):
    first = _post("https://www.instagram.com/reel/ABC123/").json()
    second = _post("https://instagram.com/reel/ABC123?igsh=zzz").json()
    assert len(db.rows) == 1
    assert second == {"status": "already_exists", "video_id": first["video_id"], "processing_status": "queued"}
    assert len(scheduled) == 1


def test_insert_race_unique_violation_returns_existing(monkeypatch):
    """Pre-check misses, insert loses the race to a concurrent request -> existing row returned."""
    winner = {"id": "winner", "status": "processing", "canonical_url": "https://www.instagram.com/reel/ABC123/"}
    lookups = iter([None, winner])
    monkeypatch.setattr(ingestion, "find_video", lambda *_: next(lookups))

    class RacingDb:
        def table(self, _):
            raise Exception('duplicate key value violates unique constraint "videos_canonical_url_key" (23505)')

    row, created = ingestion.create_or_get_video(RacingDb(), winner["canonical_url"])
    assert (row["id"], created) == ("winner", False)


def test_failed_reel_is_requeued_on_resubmission(db, scheduled):
    vid = _post().json()["video_id"]
    db.rows[0]["status"] = "failed"
    body = _post().json()
    assert body == {"status": "queued", "video_id": vid}
    assert db.rows[0]["status"] == "queued"
    assert len(db.rows) == 1 and len(scheduled) == 2


def test_wrong_secret_and_invalid_url(db, scheduled):
    assert _post(secret="nope").status_code == 401
    assert _post("https://example.com/x").status_code == 400
    assert db.rows == [] and scheduled == []


# --- processing lifecycle ---------------------------------------------------

def _queued_row(db):
    row = {"id": "vid-1", "status": "queued", "attempt_count": 0, "canonical_url": "https://www.instagram.com/reel/ABC123/"}
    db.rows.append(row)
    return row


def _stub_pipeline(monkeypatch, download=None):
    monkeypatch.setattr(
        processing, "download_reel_audio", download or (lambda url: ("/tmp/a.m4a", dt.date(2026, 1, 2), "cap"))
    )
    monkeypatch.setattr(processing, "transcribe_audio_file", lambda p: "transcript")
    monkeypatch.setattr(processing, "extract_tools_from_transcript", lambda t, caption=None: [])
    monkeypatch.setattr(processing, "upsert_tools", lambda tools, vid, d: ["t1"])


def test_processing_success_lifecycle(db, monkeypatch):
    row = _queued_row(db)
    _stub_pipeline(monkeypatch)
    result = processing.process_reel("vid-1", row["canonical_url"])
    assert result == {"video_id": "vid-1", "tool_ids": ["t1"]}
    assert [s for _, s in db.history] == ["processing", "completed"]
    assert row["status"] == "completed"
    assert row["attempt_count"] == 1
    assert row["processing_started_at"] and row["completed_at"]
    assert row["processing_error"] is None
    assert row["transcript"] == "transcript" and row["caption"] == "cap"


def test_download_failure_keeps_row_and_marks_failed(db, monkeypatch):
    row = _queued_row(db)

    def boom(url):
        raise RuntimeError("instagram rate limited")

    _stub_pipeline(monkeypatch, download=boom)
    result = processing.process_reel("vid-1", row["canonical_url"])
    assert "error" in result
    assert db.rows == [row]  # durable row survives
    assert row["status"] == "failed"
    assert row["attempt_count"] == 1
    assert "RuntimeError" in row["processing_error"] and "rate limited" in row["processing_error"]
    assert [s for _, s in db.history] == ["processing", "failed"]


def test_retry_increments_attempt_and_clears_error(db, monkeypatch):
    row = _queued_row(db)
    row.update(attempt_count=1, processing_error="old")
    _stub_pipeline(monkeypatch)
    processing.process_reel("vid-1", row["canonical_url"])
    assert row["attempt_count"] == 2 and row["processing_error"] is None and row["status"] == "completed"
