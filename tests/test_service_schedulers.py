from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db  # noqa: E402


def test_schedulers_get_put(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    # Defaults
    resp = client.get("/schedulers")
    assert resp.status_code == 200
    data = resp.json()
    sc = data["sync_character"]
    assert sc["enabled"] is True
    assert "last_run_at" in sc
    assert "next_run_at" in sc
    assert "running" in sc
    assert "queued" in sc

    # Update one job
    payload = {"sync_character": {"enabled": False, "interval": 120}}
    resp = client.put("/schedulers", json=payload)
    assert resp.status_code == 200
    data2 = resp.json()
    assert data2["sync_character"]["enabled"] is False
    assert data2["sync_character"]["interval"] == 120

    # Ensure persisted
    resp = client.get("/schedulers")
    data3 = resp.json()
    assert data3["sync_character"]["interval"] == 120
