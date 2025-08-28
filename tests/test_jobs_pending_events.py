import sys
from pathlib import Path
from fastapi.testclient import TestClient

# ensure app is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import jobs, service
from app.status import STATUS

def dummy():
    pass

def test_jobs_pending_list_updates(monkeypatch):
    jobs.clear_queue()
    STATUS["pending"] = []
    STATUS["queue"] = {}

    jobs.enqueue("a", dummy, priority="P1")
    jobs.enqueue("b", dummy, priority="P3")

    client = TestClient(service.app)
    resp = client.get("/status")
    data = resp.json()
    assert data["queue"]["P1"] == 1
    assert data["queue"]["P3"] == 1
    assert [p["job"] for p in data["pending"]] == ["b", "a"]

    jobs.run_next_job()

    resp = client.get("/status")
    data = resp.json()
    assert [p["job"] for p in data["pending"]] == ["b"]
