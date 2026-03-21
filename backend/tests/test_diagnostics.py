import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from services.assemblyai_check import check_assemblyai_connection


def test_check_assemblyai_missing_key(monkeypatch):
    import services.assemblyai_check as aac

    monkeypatch.setattr(aac, "settings", SimpleNamespace(assemblyai_api_key=""))
    out = check_assemblyai_connection()
    assert out["ok"] is False
    assert out["configured"] is False
    assert "missing" in out["message"].lower()


@patch("services.assemblyai_check.httpx.Client")
def test_check_assemblyai_401(mock_client_class):
    import services.assemblyai_check as aac

    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = ""
    mock_instance.get.return_value = mock_response
    mock_instance.__enter__.return_value = mock_instance
    mock_instance.__exit__.return_value = None
    mock_client_class.return_value = mock_instance

    with patch.object(aac, "settings", SimpleNamespace(assemblyai_api_key="bad-key")):
        out = check_assemblyai_connection()
    assert out["ok"] is False
    assert out["http_status"] == 401
    assert out["reachable"] is True


@patch("services.assemblyai_check.httpx.Client")
def test_check_assemblyai_ok(mock_client_class):
    import services.assemblyai_check as aac

    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"transcripts":[]}'
    mock_instance.get.return_value = mock_response
    mock_instance.__enter__.return_value = mock_instance
    mock_instance.__exit__.return_value = None
    mock_client_class.return_value = mock_instance

    with patch.object(aac, "settings", SimpleNamespace(assemblyai_api_key="good-key")):
        out = check_assemblyai_connection()
    assert out["ok"] is True
    assert out["http_status"] == 200


@pytest.fixture
def client():
    return TestClient(app)


@patch(
    "routers.diagnostics.check_assemblyai_connection",
    return_value={
        "service": "assemblyai",
        "ok": True,
        "message": "ok",
        "hint": "",
        "configured": True,
        "reachable": True,
        "http_status": 200,
    },
)
def test_api_diagnostics_assemblyai(mock_check, client):
    r = client.get("/api/diagnostics/assemblyai")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "assemblyai"


@patch(
    "routers.diagnostics.check_assemblyai_connection",
    return_value={"service": "assemblyai", "ok": True},
)
def test_api_diagnostics_summary(mock_check, client):
    r = client.get("/api/diagnostics/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["all_ok"] is True
    assert len(body["steps"]) == 1
    assert body["steps"][0]["name"] == "assemblyai"
