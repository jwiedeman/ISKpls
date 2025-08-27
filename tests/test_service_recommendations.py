from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db


def _seed_recommendations(con):
    con.execute(
        """
        INSERT INTO recommendations(type_id, ts_utc, net_pct, uplift_mom, daily_capacity, rationale_json)
        VALUES
        (1, '2024-01-01T00:00:00', 0.1, 0.25, 1000, '{}'),
        (2, '2024-01-02T00:00:00', 0.05, 0.30, 2000, '{}')
        """
    )
    con.commit()


def test_list_recommendations_filters(tmp_path, monkeypatch):
    # Redirect DB to temporary file and seed with sample data
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_recommendations(con)
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/recommendations", params={"min_net": 0.08})
    assert resp.status_code == 200
    data = resp.json()
    # Only one record meets the net filter
    assert len(data["results"]) == 1
    assert data["results"][0]["type_id"] == 1

    # Filter by MoM uplift should exclude both when threshold high
    resp = client.get("/recommendations", params={"min_mom": 0.35})
    assert resp.status_code == 200
    assert data["results"]
    data2 = resp.json()
    assert data2["results"] == []

