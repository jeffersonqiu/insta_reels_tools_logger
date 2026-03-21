import datetime as dt
import difflib
import json
from typing import Any

from anthropic import Anthropic

from config import settings
from db.client import get_supabase
from models.schemas import ToolExtraction


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in name.lower().strip() if ch.isalnum() or ch in {".", "-", " "})


def _fuzzy_best_match(target_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_target = _normalize_name(target_name)
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in candidates:
        cand = _normalize_name((row.get("name") or ""))
        score = difflib.SequenceMatcher(None, normalized_target, cand).ratio()
        scored.append((score, row))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best = scored[0]
    return best if best_score >= 0.86 else None


def _claude_merge_decision(existing: dict[str, Any], new: ToolExtraction) -> dict[str, Any]:
    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""
You are comparing two descriptions of the same tool to decide whether an update is warranted.

Existing record:
- functionality: {existing.get("functionality")}
- problem_solved: {existing.get("problem_solved")}
- tags: {existing.get("tags")}

New extraction from a recent video:
- functionality: {new.functionality}
- problem_solved: {new.problem_solved}
- tags: {new.tags}

Respond ONLY with a JSON object:
{{
  "should_update_functionality": true/false,
  "should_update_problem_solved": true/false,
  "should_update_tags": true/false,
  "merged_functionality": "...",
  "merged_problem_solved": "...",
  "merged_tags": [...]
}}
"""
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in resp.content if getattr(block, "text", None))
    return json.loads(raw)


def _upsert_interaction_and_link(tool_id: str, video_id: str) -> None:
    supabase = get_supabase()
    supabase.table("user_interactions").upsert(
        {"tool_id": tool_id, "status": "to_explore"},
        on_conflict="tool_id",
        ignore_duplicates=True,
    ).execute()
    supabase.table("video_tools").upsert(
        {"video_id": video_id, "tool_id": tool_id},
        on_conflict="video_id,tool_id",
        ignore_duplicates=True,
    ).execute()


def upsert_tools(tools: list[ToolExtraction], video_id: str, video_date: dt.date | None) -> list[str]:
    processed_ids: list[str] = []
    supabase = get_supabase()
    all_tools = supabase.table("tools").select("*").execute().data or []

    for item in tools:
        exact_matches = [
            t for t in all_tools if _normalize_name(t.get("name", "")) == _normalize_name(item.name)
        ]
        existing = exact_matches[0] if exact_matches else _fuzzy_best_match(item.name, all_tools)

        if existing is None:
            inserted = supabase.table("tools").insert(
                {
                    "name": item.name,
                    "functionality": item.functionality,
                    "problem_solved": item.problem_solved,
                    "tags": item.tags,
                    "first_seen_date": (video_date.isoformat() if video_date else None),
                    "source_video_ids": [video_id],
                }
            ).execute()
            tool_id = inserted.data[0]["id"]
            _upsert_interaction_and_link(tool_id, video_id)
            processed_ids.append(tool_id)
            continue

        tool_id = existing["id"]
        changed = False
        updates: dict[str, Any] = {}
        if settings.anthropic_api_key:
            decision = _claude_merge_decision(existing, item)
            if decision.get("should_update_functionality"):
                updates["functionality"] = decision.get("merged_functionality")
                changed = True
            if decision.get("should_update_problem_solved"):
                updates["problem_solved"] = decision.get("merged_problem_solved")
                changed = True
            if decision.get("should_update_tags"):
                updates["tags"] = decision.get("merged_tags")
                changed = True

        if video_date:
            old_date = existing.get("first_seen_date")
            if not old_date or video_date.isoformat() < old_date:
                updates["first_seen_date"] = video_date.isoformat()
                changed = True

        source_video_ids = existing.get("source_video_ids") or []
        if video_id not in source_video_ids:
            source_video_ids.append(video_id)
            updates["source_video_ids"] = source_video_ids
            changed = True

        if changed:
            updates["last_updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            supabase.table("tools").update(updates).eq("id", tool_id).execute()

        _upsert_interaction_and_link(tool_id, video_id)
        processed_ids.append(tool_id)

    return processed_ids
