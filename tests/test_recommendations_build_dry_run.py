from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure app package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db, config
from app import recommender


def test_recommendations_build_dry_run(tmp_path, monkeypatch):
    # Set up isolated DB
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        # populate type_trends with three candidates
        con.executemany(
            "INSERT INTO type_trends(type_id, vol_30d_avg, mom_pct) VALUES(?,?,?)",
            [
                (1, 150, 0.15),
                (2, 200, 0.20),
                (3, 180, 0.05),
            ],
        )
        now = datetime.utcnow()
        recent = (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "INSERT INTO market_snapshots(ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units) VALUES (?,?,?,?,?,?,?,?,?)",
            (recent, 1, config.STATION_ID, 10, 12, 0, 0, 0, 0),
        )
        con.execute(
            "INSERT INTO market_snapshots(ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units) VALUES (?,?,?,?,?,?,?,?,?)",
            (old, 2, config.STATION_ID, 11, 13, 0, 0, 0, 0),
        )
        con.commit()
    finally:
        con.close()

    # stub evaluate_type to avoid network
    def fake_eval(tid):
        if tid in (1, 2):
            return {
                "type_id": tid,
                "net_spread_pct": 0.05,
                "uplift_mom": 0.2,
                "daily_isk_capacity": 1000,
            }
        return None

    monkeypatch.setattr(recommender, "evaluate_type", fake_eval)

    client = TestClient(service.app)
    resp = client.post("/recommendations/build?dry_run=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidates"] == 3
    assert data["fresh_pass"] == 1
    assert data["vol_pass"] == 3
    assert data["mom_pass"] == 2
    assert data["scored"] == 2
    assert data["would_write"] == 2

    # ensure no rows written
    con = db.connect()
    try:
        cnt = con.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
    finally:
        con.close()
    assert cnt == 0
