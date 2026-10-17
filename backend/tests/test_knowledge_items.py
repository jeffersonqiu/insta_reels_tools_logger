"""Knowledge-item model: schema, extraction, processing integration, read API. No network."""

import datetime as dt
import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from models.schemas import KnowledgeExtraction, ToolExtraction
from services import extractor, processing


class FakeSupabase:
    """In-memory multi-table stand-in: select/eq/in_/order/limit/insert/update/upsert."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name):
        return _Q(self, name)


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.filters = db, name, "select", None, []
        self.conflict = None
        self._limit = None
        self._order = None

    def select(self, *_):
        return self

    def insert(self, p):
        self.op, self.payload = "insert", p
        return self

    def update(self, p):
        self.op, self.payload = "update", p
        return self

    def upsert(self, p, on_conflict=None):
        self.op, self.payload, self.conflict = "upsert", p, on_conflict
        return self

    def eq(self, c, v):
        self.filters.append((c, v))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        match = [r for r in rows if all(r.get(c) == v for c, v in self.filters)]
        if self.op == "insert":
            row = {"id": str(uuid.uuid4()), **self.payload}
            rows.append(row)
            return _R([dict(row)])
        if self.op == "upsert":
            existing = next((r for r in rows if r.get(self.conflict) == self.payload.get(self.conflict)), None)
            if existing:
                existing.update(self.payload)
                return _R([dict(existing)])
            row = {"id": str(uuid.uuid4()), **self.payload}
            rows.append(row)
            return _R([dict(row)])
        if self.op == "update":
            for r in match:
                r.update(self.payload)
            return _R([dict(r) for r in match])
        out = [dict(r) for r in match]
        if self._order:
            out.sort(key=lambda r: r.get(self._order[0]) or "", reverse=self._order[1])
        return _R(out[: self._limit] if self._limit else out)


class _R:
    def __init__(self, data):
        self.data = data


def _knowledge(tools=None) -> KnowledgeExtraction:
    return KnowledgeExtraction(
        title="Git worktrees",
        summary="Use worktrees to run parallel branches.",
        key_ideas=["one checkout per branch"],
        tools=tools or [],
        concepts=["git worktree"],
        action_items=["Try `git worktree add`"],
        tags=["devtools"],
    )


# --- schema ----------------------------------------------------------------

def test_knowledge_extraction_validation():
    k = KnowledgeExtraction.model_validate({"title": "T", "summary": "S"})
    assert k.tools == [] and k.repositories == [] and k.key_ideas == []
    with pytest.raises(ValidationError):
        KnowledgeExtraction.model_validate({"summary": "no title"})


def test_repository_url_optional():
    k = KnowledgeExtraction.model_validate(
        {"title": "T", "summary": "S", "repositories": [{"name": "foo/bar", "url": None}]}
    )
    assert k.repositories[0].url is None


# --- extractor ---------------------------------------------------------------

def _fake_claude(monkeypatch, outputs):
    calls = iter(outputs)
    seen = []
    monkeypatch.setattr(extractor, "_call_claude", lambda p, force_json_retry=False: (seen.append(force_json_retry), next(calls))[1])
    monkeypatch.setattr(extractor.settings, "anthropic_api_key", "test-key")
    return seen


def test_extract_with_tools(monkeypatch):
    payload = {
        "title": "Ruflo",
        "summary": "A tool.",
        "tools": [{"name": "ruflo", "functionality": "f", "problem_solved": "p", "tags": ["agents"]}],
    }
    _fake_claude(monkeypatch, [json.dumps(payload)])
    k = extractor.extract_knowledge("transcript", "ruflo")
    assert [t.name for t in k.tools] == ["ruflo"]
    assert extractor.extract_tools_from_transcript is not None


def test_extract_zero_tools_is_valid(monkeypatch):
    seen = _fake_claude(monkeypatch, [json.dumps({"title": "Worktrees", "summary": "S", "tools": []})])
    k = extractor.extract_knowledge("about git worktrees", None)
    assert k.tools == [] and k.title == "Worktrees"
    assert seen == [False]  # no needless second Claude call


def test_extract_retries_once_then_fails(monkeypatch):
    seen = _fake_claude(monkeypatch, ["not json", "still not json"])
    with pytest.raises(extractor.ExtractionError, match="still not json"):
        extractor.extract_knowledge("t", None)
    assert seen == [False, True]


def test_prompt_forbids_invented_urls():
    assert "never invent URLs" in extractor.SYSTEM_PROMPT


# --- processing integration -------------------------------------------------

@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    fake.tables["videos"] = [
        {"id": "vid-1", "status": "queued", "attempt_count": 0, "canonical_url": "https://www.instagram.com/reel/A/"}
    ]
    monkeypatch.setattr("services.processing.get_supabase", lambda: fake)
    monkeypatch.setattr(processing, "download_reel_audio", lambda u: ("/tmp/a.m4a", dt.date(2026, 1, 2), "cap"))
    monkeypatch.setattr(processing, "transcribe_audio_file", lambda p: "transcript")
    return fake


def test_success_creates_knowledge_item_and_upserts_tools(db, monkeypatch):
    tool = ToolExtraction(name="ruflo", functionality="f", problem_solved="p", tags=[])
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: _knowledge([tool]))
    upserted = []
    monkeypatch.setattr(processing, "upsert_tools", lambda tools, vid, d: (upserted.append((tools, vid)), ["t1"])[1])

    result = processing.process_reel("vid-1", "https://www.instagram.com/reel/A/")

    assert result["tool_ids"] == ["t1"]
    assert upserted == [([tool], "vid-1")]
    items = db.tables["knowledge_items"]
    assert len(items) == 1
    assert items[0]["video_id"] == "vid-1" and items[0]["title"] == "Git worktrees"
    assert items[0]["source_url"] == "https://www.instagram.com/reel/A/"
    assert items[0]["raw_extraction"]["tools"][0]["name"] == "ruflo"
    video = db.tables["videos"][0]
    assert video["status"] == "completed"
    assert video["raw_extraction"][0]["name"] == "ruflo"  # legacy shape preserved


def test_retry_updates_same_knowledge_item(db, monkeypatch):
    monkeypatch.setattr(processing, "upsert_tools", lambda *a: [])
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: _knowledge())
    processing.process_reel("vid-1", "u")
    first_id = db.tables["knowledge_items"][0]["id"]

    changed = _knowledge()
    changed.title = "Updated title"
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: changed)
    processing.process_reel("vid-1", "u")

    items = db.tables["knowledge_items"]
    assert len(items) == 1 and items[0]["id"] == first_id and items[0]["title"] == "Updated title"
    assert db.tables["videos"][0]["attempt_count"] == 2


def test_extraction_failure_not_completed_and_no_item(db, monkeypatch):
    def boom(t, caption=None):
        raise extractor.ExtractionError("bad json")

    monkeypatch.setattr(processing, "extract_knowledge", boom)
    processing.process_reel("vid-1", "u")
    assert db.tables["videos"][0]["status"] == "failed"
    assert "bad json" in db.tables["videos"][0]["processing_error"]
    assert "knowledge_items" not in db.tables


def test_tool_upsert_failure_not_completed(db, monkeypatch):
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: _knowledge())

    def boom(*a):
        raise RuntimeError("tools down")

    monkeypatch.setattr(processing, "upsert_tools", boom)
    processing.process_reel("vid-1", "u")
    assert db.tables["videos"][0]["status"] == "failed"  # never completed with partial output


def test_knowledge_persist_failure_not_completed(db, monkeypatch):
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: _knowledge())
    tools_called = []
    monkeypatch.setattr(processing, "upsert_tools", lambda *a: tools_called.append(1) or [])

    def boom(*a):
        raise RuntimeError("db down")

    monkeypatch.setattr(processing, "upsert_knowledge_item", boom)
    processing.process_reel("vid-1", "u")
    assert db.tables["videos"][0]["status"] == "failed" and tools_called == []


# --- read API ---------------------------------------------------------------

@pytest.fixture
def api(monkeypatch):
    fake = FakeSupabase()
    fake.tables["videos"] = [
        {
            "id": "v1", "instagram_url": "https://www.instagram.com/reel/A/", "caption": "cap",
            "transcript": "tr", "video_created_at": "2026-01-02", "status": "completed", "secret_col": "x",
        }
    ]
    fake.tables["knowledge_items"] = [
        {"id": "k1", "video_id": "v1", "title": "Old", "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": "k2", "video_id": "v1", "title": "New", "created_at": "2026-02-01T00:00:00+00:00"},
    ]
    monkeypatch.setattr("routers.items.get_supabase", lambda: fake)
    return TestClient(app)


def test_list_items_newest_first_with_limit(api):
    r = api.get("/api/items")
    assert r.status_code == 200
    assert [i["id"] for i in r.json()] == ["k2", "k1"]
    assert r.headers["cache-control"].startswith("no-store")
    assert [i["id"] for i in api.get("/api/items?limit=1").json()] == ["k2"]
    assert api.get("/api/items?limit=0").status_code == 422


def test_list_items_empty(monkeypatch):
    monkeypatch.setattr("routers.items.get_supabase", lambda: FakeSupabase())
    r = TestClient(app).get("/api/items")
    assert r.status_code == 200 and r.json() == []


def test_get_item_includes_source_video_fields(api):
    r = api.get("/api/items/k2")
    assert r.status_code == 200
    body = r.json()
    assert body["item"]["title"] == "New"
    # (the fake ignores column selection; the router requests exactly these fields)
    assert set(body["video"]) >= {"instagram_url", "caption", "transcript", "video_created_at", "status"}
    assert body["video"]["instagram_url"] == "https://www.instagram.com/reel/A/"


def test_get_unknown_item_404(api):
    assert api.get("/api/items/nope").status_code == 404
