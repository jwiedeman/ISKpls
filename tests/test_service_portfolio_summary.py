from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app.pricing import default_fees


def _seed_portfolio(con):
    # Wallet balance
    con.execute(
        "INSERT INTO wallet_snapshots(ts_utc, balance) VALUES(datetime('now'), 100.0)"
    )
    # Buy order with escrow 5
    con.execute(
        """
        INSERT INTO char_orders(
          order_id, is_buy, region_id, location_id, type_id, price,
          volume_total, volume_remain, issued, duration, range,
          min_volume, escrow, last_seen, state)
        VALUES (1,1,10000002,60003760,1,10,1,1,datetime('now'),30,'region',1,5,datetime('now'),'open')
        """
    )
    # Sell order with price 20
    con.execute(
        """
        INSERT INTO char_orders(
          order_id, is_buy, region_id, location_id, type_id, price,
          volume_total, volume_remain, issued, duration, range,
          min_volume, escrow, last_seen, state)
        VALUES (2,0,10000002,60003760,1,20,1,1,datetime('now'),30,'region',1,0,datetime('now'),'open')
        """
    )
    # Inventory asset: 2 units of type 1
    con.execute(
        """
        INSERT INTO assets(item_id, type_id, quantity, is_singleton, location_id, location_type, location_flag, updated)
        VALUES (1,1,2,0,60003760,'station','hangar',datetime('now'))
        """
    )
    # Valuations for type 1
    con.execute(
        "INSERT INTO type_valuations(type_id, quicksell_bid, mark_ask, updated) VALUES (1,8,12,datetime('now'))"
    )
    # Realized trades
    con.execute(
        "INSERT INTO realized_trades(trade_id, ts_utc, type_id, qty, sell_unit_price, cost_total, tax, broker_fee, pnl)"
        " VALUES('a', datetime('now','-3 days'), 1,1,20,10,1,1,5)"
    )
    con.execute(
        "INSERT INTO realized_trades(trade_id, ts_utc, type_id, qty, sell_unit_price, cost_total, tax, broker_fee, pnl)"
        " VALUES('b', datetime('now','-20 days'), 1,1,20,10,1,1,7)"
    )
    con.commit()


def test_portfolio_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_portfolio(con)
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/portfolio/summary", params={"basis": "mark"})
    assert resp.status_code == 200
    data = resp.json()
    fees = default_fees()
    sell_net = 20 * (1 - fees.sell_total)
    sell_value_qs = 16.0 + sell_net
    sell_value_mk = 24.0 + sell_net
    assert data["liquid"] == 100.0
    assert data["buy_escrow"] == 5.0
    assert abs(data["sell_value_quicksell"] - sell_value_qs) < 1e-6
    assert abs(data["sell_value_mark"] - sell_value_mk) < 1e-6
    assert data["nav_quicksell"] == 100.0 + 5.0 + sell_value_qs
    assert data["nav_mark"] == 100.0 + 5.0 + sell_value_mk
    assert data["realized_7d"] == 5.0
    assert data["realized_30d"] == 12.0
    assert data["basis"] == "mark"
