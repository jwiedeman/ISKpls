from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app import type_cache


def _seed_orders(con):
    con.execute(
        """
        INSERT INTO char_orders(
          order_id, is_buy, region_id, location_id, type_id, price,
          volume_total, volume_remain, issued, duration, range,
          min_volume, escrow, last_seen, state)
        VALUES
          (1,1,10000002,60003760,1,10,10,5,'2024-01-01',30,'region',1,100,'2024-01-01','open'),
          (2,0,10000002,60003760,1,20,5,5,'2024-01-01',30,'region',1,0,'2024-01-01','closed')
        """
    )
    con.commit()


def _seed_types(con):
    con.execute(
        """
        INSERT INTO types(type_id, name, group_id) VALUES (1, 'Foo', 10)
        """
    )
    con.commit()


def test_list_open_orders(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_types(con)
        _seed_orders(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/orders/open")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["orders"]) == 1
    order = data["orders"][0]
    assert order["order_id"] == 1
    assert order["is_buy"] is True
    assert order["fill_pct"] == 0.5
    assert order["type_name"] == "Foo"
