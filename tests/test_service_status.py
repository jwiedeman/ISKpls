from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service
from app.status import STATUS


def test_status_returns_cache():
    client = TestClient(service.app)
    STATUS["inflight"] = [{"job": "sample", "id": "j-1"}]
    STATUS["last_runs"] = [{"job": "sync", "ok": True, "ts": "2024-01-01T00:00:00Z", "ms": 100}]
    STATUS["counts"] = {"jobs_10m": 1}
    STATUS["esi"] = {"remain": 100, "reset": 10}

    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["inflight"][0]["job"] == "sample"
    assert data["last_runs"][0]["job"] == "sync"
    assert data["counts"]["jobs_10m"] == 1
    assert data["esi"]["remain"] == 100
