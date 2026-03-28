"""Unit tests for tool search matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers.tools import tool_matches_search


def test_empty_query_matches_all():
    t = {"name": "Foo", "functionality": None, "problem_solved": None, "tags": [], "notes": None}
    assert tool_matches_search(t, "") is True
    assert tool_matches_search(t, "   ") is True


def test_matches_name():
    t = {"name": "MCP servers", "functionality": "", "problem_solved": "", "tags": [], "notes": None}
    assert tool_matches_search(t, "mcp") is True
    assert tool_matches_search(t, "servers") is True
    assert tool_matches_search(t, "nomatch") is False


def test_matches_functionality_and_problem():
    t = {
        "name": "X",
        "functionality": "Uses Claude Code",
        "problem_solved": "JSON schema",
        "tags": [],
        "notes": None,
    }
    assert tool_matches_search(t, "claude") is True
    assert tool_matches_search(t, "json") is True


def test_matches_tags():
    t = {"name": "Y", "functionality": None, "problem_solved": None, "tags": ["devtools", "agents"], "notes": None}
    assert tool_matches_search(t, "agents") is True
    assert tool_matches_search(t, "DEVTOOLS") is True


def test_matches_notes():
    t = {"name": "Z", "functionality": None, "problem_solved": None, "tags": [], "notes": "Try next week"}
    assert tool_matches_search(t, "week") is True
