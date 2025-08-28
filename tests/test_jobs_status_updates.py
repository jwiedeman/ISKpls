from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app.jobs import record_job
from app.status import STATUS


def test_record_job_updates_status(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()

    # reset status snapshot
    STATUS["last_runs"] = []
    STATUS["counts"] = {}

    record_job("sample", True, {"ms": 50})

    client = TestClient(service.app)
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_runs"][0]["job"] == "sample"
    assert data["last_runs"][0]["ok"] is True
    assert data["counts"]["jobs_10m"] == 1
