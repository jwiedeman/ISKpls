from fastapi.testclient import TestClient
import sys
from pathlib import Path
import pytest

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db, type_cache
from app.config import STATION_ID
from app.market import margin_after_fees


def _seed(con):
    con.execute(
        """
        INSERT INTO types(type_id, name, group_id) VALUES (1, 'Foo', 10)
        """,
    )
    con.execute(
        """
        INSERT INTO market_snapshots(
            ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES ('2024-01-01', 1, ?, 10, 12, 1, 1, 0, 0)
        """,
        (STATION_ID,),
    )
    con.commit()


def test_reprice_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/orders/reprice", params={"type_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type_name"] == "Foo"
    assert data["best_bid"] == 10
    assert data["best_ask"] == 12
    assert data["buy_price"] == pytest.approx(10.01)
    assert data["sell_price"] == pytest.approx(11.99)
    expected_buy = margin_after_fees(10.01, 12) / 10.01
    expected_sell = margin_after_fees(10, 11.99) / 10
    assert data["buy_net_pct"] == pytest.approx(expected_buy)
    assert data["sell_net_pct"] == pytest.approx(expected_sell)
