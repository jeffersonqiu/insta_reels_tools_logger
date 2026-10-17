"""Knowledge-item model: schema, extraction, processing integration, read API. No network."""

import datetime as dt
import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from models.schemas import KnowledgeExtraction, ToolExtraction
from services import deduplicator, extractor, processing

VIDEO_ID = "10000000-0000-0000-0000-000000000001"
SECOND_VIDEO_ID = "10000000-0000-0000-0000-000000000002"
OLD_ITEM_ID = "20000000-0000-0000-0000-000000000001"
NEW_ITEM_ID = "20000000-0000-0000-0000-000000000002"


class FakeSupabase:
    """In-memory multi-table stand-in including projections and conflict handling."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name):
        return _Q(self, name)


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.filters = db, name, "select", None, []
        self.conflict = None
        self._limit = None
        self._orders = []
        self.columns = "*"
        self.ignore_duplicates = False
        self._offset = 0

    def select(self, columns="*"):
        self.columns = columns
        return self

    def insert(self, p):
        self.op, self.payload = "insert", p
        return self

    def update(self, p):
        self.op, self.payload = "update", p
        return self

    def upsert(self, p, on_conflict=None, ignore_duplicates=False):
        self.op, self.payload, self.conflict = "upsert", p, on_conflict
        self.ignore_duplicates = ignore_duplicates
        return self

    def eq(self, c, v):
        self.filters.append(lambda row: row.get(c) == v)
        return self

    def in_(self, c, values):
        self.filters.append(lambda row: row.get(c) in values)
        return self

    def lt(self, c, value):
        self.filters.append(lambda row: row.get(c) is not None and row[c] < value)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, col, desc=False):
        self._orders.append((col, desc))
        return self

    def range(self, start, end):
        self._offset, self._limit = start, end - start + 1
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        match = [r for r in rows if all(predicate(r) for predicate in self.filters)]
        if self.op == "insert":
            row = {"id": str(uuid.uuid4()), **self.payload}
            rows.append(row)
            return _R([dict(row)])
        if self.op == "upsert":
            keys = self.conflict.split(",")
            existing = next((r for r in rows if all(r.get(k) == self.payload.get(k) for k in keys)), None)
            if existing:
                if self.ignore_duplicates:
                    return _R([])
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
        for col, desc in reversed(self._orders):
            out.sort(key=lambda r: r.get(col) or "", reverse=desc)
        out = out[self._offset:]
        out = out[: self._limit] if self._limit else out
        if self.columns != "*":
            out = [{key.strip(): row.get(key.strip()) for key in self.columns.split(",")} for row in out]
        return _R(out)


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


def test_anthropic_request_includes_transcript_and_caption(monkeypatch):
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"title": "Worktrees", "summary": "S"}))])

    monkeypatch.setattr(extractor.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(extractor, "Anthropic", lambda **kwargs: SimpleNamespace(messages=SimpleNamespace(create=create)))
    assert extractor.extract_knowledge("audio about branches", "creator's caption").title == "Worktrees"
    assert len(requests) == 1
    message = requests[0]["messages"][0]["content"]
    assert "audio about branches" in message and "creator's caption" in message


def test_invalid_extraction_schema_retries_then_succeeds(monkeypatch):
    seen = _fake_claude(monkeypatch, [
        json.dumps({"title": "Missing summary"}),
        json.dumps({"title": "Valid", "summary": "S", "repositories": [{"name": "project", "url": None}]}),
    ])
    assert extractor.extract_knowledge("transcript").repositories[0].url is None
    assert seen == [False, True]


def test_legacy_tool_extraction_helper(monkeypatch):
    payload = {"title": "T", "summary": "S", "tools": [{"name": "Tool", "functionality": "f", "problem_solved": "p"}]}
    _fake_claude(monkeypatch, [json.dumps(payload)])
    tools = extractor.extract_tools_from_transcript("transcript", "caption")
    assert tools == [ToolExtraction(name="Tool", functionality="f", problem_solved="p")]


# --- processing integration -------------------------------------------------

@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    fake.tables["videos"] = [
        {
            "id": "vid-1", "status": "queued", "attempt_count": 0,
            "canonical_url": "https://www.instagram.com/reel/A/", "instagram_url": "https://www.instagram.com/reel/A/",
        }
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
    def failing_tool_upsert(*args):
        raise RuntimeError("temporary tool failure")

    monkeypatch.setattr(processing, "upsert_tools", failing_tool_upsert)
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: _knowledge())
    processing.process_reel("vid-1", "u")
    assert db.tables["videos"][0]["status"] == "failed"
    first_id = db.tables["knowledge_items"][0]["id"]

    changed = _knowledge()
    changed.title = "Updated title"
    monkeypatch.setattr(processing, "extract_knowledge", lambda t, caption=None: changed)
    monkeypatch.setattr(processing, "upsert_tools", lambda *args: [])
    db.tables["videos"][0]["status"] = "queued"  # webhook resubmission wins the failed -> queued transition
    processing.process_reel("vid-1", "u")

    items = db.tables["knowledge_items"]
    assert len(items) == 1 and items[0]["id"] == first_id and items[0]["title"] == "Updated title"
    assert db.tables["videos"][0]["attempt_count"] == 2
    assert db.tables["videos"][0]["status"] == "completed"
    assert db.tables["videos"][0]["processing_error"] is None


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


def test_processing_with_zero_tools_still_saves_knowledge(db, monkeypatch):
    monkeypatch.setattr(deduplicator, "get_supabase", lambda: db)
    monkeypatch.setattr(processing, "extract_knowledge", lambda *args, **kwargs: _knowledge())
    result = processing.process_reel("vid-1", "https://www.instagram.com/reel/A/")
    assert result == {"video_id": "vid-1", "tool_ids": []}
    assert db.tables["videos"][0]["status"] == "completed"
    assert db.tables["videos"][0]["raw_extraction"] == []
    assert db.tables["knowledge_items"][0]["concepts"] == ["git worktree"]
    assert "transcript" not in db.tables["knowledge_items"][0]
    assert "caption" not in db.tables["knowledge_items"][0]
    assert db.tables.get("tools", []) == [] and db.tables.get("video_tools", []) == []


def test_processing_stores_new_tools_and_links(db, monkeypatch):
    monkeypatch.setattr(deduplicator, "get_supabase", lambda: db)
    tool = ToolExtraction(name="New tool", functionality="f", problem_solved="p", tags=["agents"])
    monkeypatch.setattr(processing, "extract_knowledge", lambda *args, **kwargs: _knowledge([tool]))
    result = processing.process_reel("vid-1", "https://www.instagram.com/reel/A/")
    stored = db.tables["tools"][0]
    assert result["tool_ids"] == [stored["id"]]
    assert stored["name"] == "New tool" and stored["source_video_ids"] == ["vid-1"]
    assert db.tables["video_tools"][0]["tool_id"] == stored["id"]
    assert db.tables["user_interactions"][0]["status"] == "to_explore"


@pytest.mark.parametrize("status", ["implemented", "not_interested"])
def test_reprocessing_preserves_tool_status_and_existing_apis(db, monkeypatch, status):
    monkeypatch.setattr(deduplicator, "get_supabase", lambda: db)
    monkeypatch.setattr("routers.tools.get_supabase", lambda: db)
    monkeypatch.setattr("routers.videos.get_supabase", lambda: db)
    monkeypatch.setattr(deduplicator.settings, "anthropic_api_key", "test-key")
    comparisons = []

    def merge(existing, new):
        comparisons.append((existing["id"], new.name))
        return {"should_update_functionality": False, "should_update_problem_solved": False, "should_update_tags": False}

    monkeypatch.setattr(deduplicator, "_claude_merge_decision", merge)
    db.tables["tools"] = [{
        "id": "tool-1", "name": "ruflo", "functionality": "Existing description", "problem_solved": "Existing problem",
        "tags": ["agents"], "first_seen_date": "2026-02-01", "source_video_ids": ["older-video"],
    }]
    interaction = {"id": "interaction-1", "tool_id": "tool-1", "status": status, "notes": "Keep my notes"}
    db.tables["user_interactions"] = [dict(interaction)]
    tool = ToolExtraction(name="ruflo", functionality="Rephrasing", problem_solved="Same problem", tags=["agents"])
    monkeypatch.setattr(processing, "extract_knowledge", lambda *args, **kwargs: _knowledge([tool]))

    for _ in range(2):
        db.tables["videos"][0]["status"] = "queued"
        assert "error" not in processing.process_reel("vid-1", "https://www.instagram.com/reel/A/")

    assert comparisons == [("tool-1", "ruflo"), ("tool-1", "ruflo")]
    assert db.tables["user_interactions"] == [interaction]
    assert len(db.tables["tools"]) == len(db.tables["knowledge_items"]) == len(db.tables["video_tools"]) == 1
    stored = db.tables["tools"][0]
    assert stored["functionality"] == "Existing description"
    assert stored["source_video_ids"] == ["older-video", "vid-1"]
    assert stored["first_seen_date"] == "2026-01-02"

    client = TestClient(app)
    tools_response = client.get(f"/api/tools?status={status}")
    assert tools_response.status_code == 200
    assert tools_response.json()[0]["status"] == status
    assert tools_response.json()[0]["notes"] == "Keep my notes"
    assert len(tools_response.json()[0]["source_videos"]) == 1
    assert client.get("/api/tools/counts").json()[status] == 1
    assert client.get("/api/tools/tags").json() == ["agents"]
    video_response = client.get("/api/videos/vid-1")
    assert video_response.status_code == 200
    assert video_response.json()["raw_extraction"] == [tool.model_dump()]
    assert video_response.json()["tools"][0]["status"] == status


# --- read API ---------------------------------------------------------------

@pytest.fixture
def api(monkeypatch):
    fake = FakeSupabase()
    fake.tables["videos"] = [
        {
            "id": VIDEO_ID, "instagram_url": "https://www.instagram.com/reel/A/", "caption": "cap",
            "transcript": "tr", "video_created_at": "2026-01-02", "status": "completed", "secret_col": "x",
        },
        {"id": SECOND_VIDEO_ID, "instagram_url": "https://www.instagram.com/reel/B/", "status": "completed"},
    ]
    fake.tables["knowledge_items"] = [
        {"id": OLD_ITEM_ID, "video_id": SECOND_VIDEO_ID, "title": "Old", "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": NEW_ITEM_ID, "video_id": VIDEO_ID, "title": "New", "created_at": "2026-02-01T00:00:00+00:00"},
    ]
    monkeypatch.setattr("routers.items.get_supabase", lambda: fake)
    return TestClient(app)


def test_list_items_newest_first_with_limit(api):
    r = api.get("/api/items")
    assert r.status_code == 200
    assert [i["id"] for i in r.json()] == [NEW_ITEM_ID, OLD_ITEM_ID]
    assert r.headers["cache-control"].startswith("no-store")
    assert [i["id"] for i in api.get("/api/items?limit=1").json()] == [NEW_ITEM_ID]
    assert api.get("/api/items?limit=0").status_code == 422


def test_list_items_empty(monkeypatch):
    monkeypatch.setattr("routers.items.get_supabase", lambda: FakeSupabase())
    r = TestClient(app).get("/api/items")
    assert r.status_code == 200 and r.json() == []


def test_item_pagination_boundaries(api):
    assert [item['id'] for item in api.get('/api/items?limit=1&offset=1').json()] == [OLD_ITEM_ID]
    assert api.get('/api/items?offset=2').json() == []
    assert api.get('/api/items?offset=-1').status_code == 422
    assert api.get('/api/items?limit=201').status_code == 422


def test_item_pagination_has_stable_order_for_equal_timestamps(monkeypatch):
    fake = FakeSupabase()
    fake.tables['knowledge_items'] = [
        {'id': OLD_ITEM_ID, 'created_at': '2026-01-01T00:00:00+00:00'},
        {'id': NEW_ITEM_ID, 'created_at': '2026-01-01T00:00:00+00:00'},
    ]
    monkeypatch.setattr('routers.items.get_supabase', lambda: fake)
    api = TestClient(app)
    assert api.get('/api/items?limit=1').json()[0]['id'] == NEW_ITEM_ID
    assert api.get('/api/items?limit=1&offset=1').json()[0]['id'] == OLD_ITEM_ID


def test_get_item_includes_source_video_fields(api):
    r = api.get(f"/api/items/{NEW_ITEM_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["item"]["title"] == "New"
    assert set(body["video"]) == {"id", "instagram_url", "caption", "transcript", "video_created_at", "status"}
    assert body["video"]["instagram_url"] == "https://www.instagram.com/reel/A/"


def test_get_unknown_item_404(api):
    assert api.get("/api/items/20000000-0000-0000-0000-000000000003").status_code == 404


def test_get_malformed_item_id_rejected_before_database(monkeypatch):
    def unexpected_database_access():
        pytest.fail("Malformed UUID must not reach Postgres")

    monkeypatch.setattr("routers.items.get_supabase", unexpected_database_access)
    assert TestClient(app).get("/api/items/not-a-uuid").status_code == 422
