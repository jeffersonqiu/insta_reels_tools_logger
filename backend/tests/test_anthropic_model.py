"""Both paid Claude request paths must use the configured, supported model."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from models.schemas import ToolExtraction
from services import deduplicator, extractor


@pytest.mark.parametrize("override", [None, "  custom-model-id  "])
def test_extraction_and_comparison_share_model(monkeypatch, override):
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    if override is not None:
        monkeypatch.setenv("ANTHROPIC_MODEL", override)
    configured = Settings(_env_file=None).anthropic_model
    assert configured == (override.strip() if override else "claude-sonnet-4-6")
    monkeypatch.setattr(extractor.settings, "anthropic_model", configured)
    monkeypatch.setattr(extractor.settings, "anthropic_api_key", "test-key")
    requests = []
    outputs = iter([
        {"title": "Agents", "summary": "A visual workflow."},
        {"should_update_functionality": False},
    ])

    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(next(outputs)))])

    fake_client = lambda **kwargs: SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(extractor, "Anthropic", fake_client)
    monkeypatch.setattr(deduplicator, "Anthropic", fake_client)
    assert extractor.extract_knowledge("Agent workflow").title == "Agents"
    decision = deduplicator._claude_merge_decision(
        {"name": "Tool"}, ToolExtraction(name="Tool", functionality="f", problem_solved="p")
    )
    assert decision["should_update_functionality"] is False
    assert [request["model"] for request in requests] == [configured, configured]


def test_blank_model_configuration_fails_before_processing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "  ")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
