from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db, valuation


def _seed_data(con):
    # Asset with type_id 1
    con.execute(
        """
        INSERT INTO assets(item_id, type_id, quantity, is_singleton, location_id, location_type, location_flag, updated)
        VALUES (1,1,1,0,60003760,'station','hangar','2024-01-01')
        """
    )
    # Order with type_id 2
    con.execute(
        """
        INSERT INTO char_orders(
          order_id, is_buy, region_id, location_id, type_id, price,
          volume_total, volume_remain, issued, duration, range,
          min_volume, escrow, last_seen, state)
        VALUES (1,1,10000002,60003760,2,10,1,1,'2024-01-01',30,'region',1,0,'2024-01-01','open')
        """
    )
    con.commit()


def test_recompute_valuations(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_data(con)
    finally:
        con.close()

    # Stub market lookup to deterministic values
    monkeypatch.setattr(
        valuation,
        "best_bid_ask_station",
        lambda tid, station, region: (tid * 10.0, tid * 20.0),
    )

    events = []

    async def fake_broadcast(evt):
        events.append(evt)

    monkeypatch.setattr("app.emit.broadcast", fake_broadcast)

    client = TestClient(service.app)
    resp = client.post("/valuations/recompute")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    con = db.connect()
    try:
        rows = con.execute(
            "SELECT type_id, quicksell_bid, mark_ask FROM type_valuations ORDER BY type_id"
        ).fetchall()
    finally:
        con.close()
    assert rows == [(1, 10.0, 20.0), (2, 20.0, 40.0)]

    profit_evt = next(e for e in events if e.get("type") == "pipeline.profit.updated")
    assert profit_evt["count"] == 2
    assert "as_of" in profit_evt
