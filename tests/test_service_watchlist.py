import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import service, db


def test_watchlist_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    resp = client.get("/watchlist")
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    resp = client.post("/watchlist/42")
    assert resp.status_code == 200

    resp = client.get("/watchlist")
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["type_id"] == 42

    resp = client.delete("/watchlist/42")
    assert resp.status_code == 200

    resp = client.get("/watchlist")
    assert resp.json()["items"] == []
