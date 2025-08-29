from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app.config import STATION_ID


def test_inventory_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "INSERT INTO market_snapshots(ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units) VALUES (?,?,?,?,?,?,?,?,?)",
            (recent, 1, STATION_ID, 10, 12, 0, 0, 0, 0),
        )
        con.execute(
            "INSERT INTO market_snapshots(ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units) VALUES (?,?,?,?,?,?,?,?,?)",
            (old, 2, STATION_ID, 11, 13, 0, 0, 0, 0),
        )
        con.commit()
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/inventory/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["types_indexed"] == 2
    assert data["books_last_10m"] == 1
    assert data["oldest_snapshot"]["type_id"] == 2
    assert data["median_snapshot_age_ms"] > 0
