"""The opt-in historical backfill must honor its cost controls."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import backfill_knowledge_items as backfill
from test_knowledge_items import FakeSupabase, _knowledge


@pytest.fixture
def backfill_db(monkeypatch):
    db = FakeSupabase()
    db.tables["videos"] = [
        {"id": "existing", "status": "completed", "instagram_url": "existing-url", "transcript": "t"},
        {"id": "empty", "status": "completed", "instagram_url": "empty-url", "transcript": ""},
        {"id": "failed", "status": "failed", "instagram_url": "failed-url", "transcript": "t"},
        {"id": "new-1", "status": "completed", "instagram_url": "new-url-1", "transcript": "t", "caption": "c"},
        {"id": "new-2", "status": "completed", "instagram_url": "new-url-2", "transcript": "t"},
    ]
    db.tables["knowledge_items"] = [{"id": "item-1", "video_id": "existing"}]
    monkeypatch.setattr(backfill, "get_supabase", lambda: db)
    return db


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_backfill_rejects_nonpositive_limit_before_database(monkeypatch, limit):
    monkeypatch.setattr(sys, "argv", ["backfill_knowledge_items.py", "--limit", limit])
    monkeypatch.setattr(backfill, "get_supabase", lambda: pytest.fail("Invalid limit must not access the database"))
    with pytest.raises(SystemExit) as error:
        backfill.main()
    assert error.value.code == 2


def test_backfill_dry_run_never_calls_llm_or_writes(backfill_db, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["backfill_knowledge_items.py", "--dry-run"])
    monkeypatch.setattr(backfill, "extract_knowledge", lambda *a, **kw: pytest.fail("Dry run must not call Anthropic"))
    monkeypatch.setattr(backfill, "upsert_knowledge_item", lambda *a: pytest.fail("Dry run must not write"))
    backfill.main()
    output = capsys.readouterr().out
    assert "would process new-1" in output and "would process new-2" in output
    assert "would process existing" not in output and "would process failed" not in output
    assert backfill_db.tables["knowledge_items"] == [{"id": "item-1", "video_id": "existing"}]


def test_backfill_limits_paid_extraction_to_missing_items(backfill_db, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["backfill_knowledge_items.py", "--limit", "1"])
    calls = []

    def extract(transcript, caption=None):
        calls.append((transcript, caption))
        return _knowledge()

    monkeypatch.setattr(backfill, "extract_knowledge", extract)
    backfill.main()
    assert calls == [("t", "c")]
    assert [item["video_id"] for item in backfill_db.tables["knowledge_items"]] == ["existing", "new-1"]
    assert "tools" not in backfill_db.tables and "video_tools" not in backfill_db.tables
