import sys
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_ok(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr("main.get_supabase", lambda: mock_client)

    client = TestClient(app)
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    mock_client.table.assert_called_once_with("videos")
    mock_client.table.return_value.select.assert_called_once_with("id")
    mock_client.table.return_value.select.return_value.limit.assert_called_once_with(1)
    mock_client.table.return_value.select.return_value.limit.return_value.execute.assert_called_once()


def test_health_db_unavailable(monkeypatch):
    secret_error = "secret supabase connection failed xyz"

    def fail_get_supabase():
        raise RuntimeError(secret_error)

    monkeypatch.setattr("main.get_supabase", fail_get_supabase)

    client = TestClient(app)
    response = client.get("/health/db")

    assert response.status_code == 503
    body = response.json()
    assert body == {"detail": "database unavailable"}
    assert secret_error not in response.text
    assert "xyz" not in response.text


def test_health_db_query_failure(monkeypatch):
    secret_error = "paused project dns lookup failed abc123"
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = (
        Exception(secret_error)
    )
    monkeypatch.setattr("main.get_supabase", lambda: mock_client)

    client = TestClient(app)
    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
    assert secret_error not in response.text
    assert "abc123" not in response.text
