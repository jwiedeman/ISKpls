from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app.pricing import default_fees


def _seed_portfolio(con):
    # Wallet balance
    con.execute(
        "INSERT INTO wallet_snapshots(ts_utc, balance) VALUES('2024-01-01T00:00:00', 100.0)"
    )
    # Buy order with escrow 5
    con.execute(
        """
        INSERT INTO char_orders(
          order_id, is_buy, region_id, location_id, type_id, price,
          volume_total, volume_remain, issued, duration, range,
          min_volume, escrow, last_seen, state)
        VALUES (1,1,10000002,60003760,1,10,1,1,'2024-01-01',30,'region',1,5,'2024-01-01','open')
        """
    )
    # Sell order with price 20
    con.execute(
        """
        INSERT INTO char_orders(
          order_id, is_buy, region_id, location_id, type_id, price,
          volume_total, volume_remain, issued, duration, range,
          min_volume, escrow, last_seen, state)
        VALUES (2,0,10000002,60003760,1,20,1,1,'2024-01-01',30,'region',1,0,'2024-01-01','open')
        """
    )
    # Inventory asset: 2 units of type 1
    con.execute(
        """
        INSERT INTO assets(item_id, type_id, quantity, is_singleton, location_id, location_type, location_flag, updated)
        VALUES (1,1,2,0,60003760,'station','hangar','2024-01-01')
        """
    )
    # Valuations for type 1
    con.execute(
        "INSERT INTO type_valuations(type_id, quicksell_bid, mark_ask, updated) VALUES (1,8,12,'2024-01-01')"
    )
    con.commit()


def test_portfolio_nav_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_portfolio(con)
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/portfolio/nav")
    assert resp.status_code == 200
    data = resp.json()

    # Expected calculations
    fees = default_fees()
    sell_net = 20 * (1 - fees.sell_total)
    assert data["wallet_balance"] == 100.0
    assert data["buy_escrow"] == 5.0
    assert data["sell_gross"] == 20.0
    assert data["inventory_quicksell"] == 16.0
    assert data["inventory_mark"] == 24.0
    assert data["nav_quicksell"] == 100.0 + 5.0 + 16.0 + sell_net
    assert data["nav_mark"] == 100.0 + 5.0 + 24.0 + sell_net
