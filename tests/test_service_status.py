from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db, jobs, esi


def test_status_returns_queue_and_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    jobs.record_job("sample", True, {"info": 1})
    jobs.JOB_QUEUE = ["refresh_assets", "recs"]
    jobs.IN_FLIGHT = {"name": "sync", "started": "2024-01-01T00:00:00"}
    esi.ERROR_LIMIT_REMAIN = 88
    esi.ERROR_LIMIT_RESET = 17

    client = TestClient(service.app)
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["name"] == "sample"
    assert data["jobs"][0]["ok"] is True
    assert data["queue"] == ["refresh_assets", "recs"]
    assert data["in_flight"]["name"] == "sync"
    assert data["counts"]["10m"] == 1
    assert data["counts"]["1h"] == 1
    assert data["counts"]["24h"] == 1
    assert data["esi"]["error_limit_remain"] == 88
    assert data["esi"]["error_limit_reset"] == 17
