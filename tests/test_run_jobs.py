from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db  # noqa: E402


def test_run_jobs_known(monkeypatch, tmp_path):
    monkeypatch.setenv("DISABLE_BACKGROUND_JOBS", "1")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    assert client.post("/jobs/snapshot_orders/run").status_code == 200
    assert client.post("/jobs/refresh_trends/run").status_code == 200
    assert client.post("/jobs/refresh_type_valuations/run").status_code == 200
    assert client.post("/jobs/sync_character/run").status_code == 200
    assert client.post("/jobs/recommender_scan/run").status_code == 200
    assert client.post("/jobs/unknown/run").status_code == 404
