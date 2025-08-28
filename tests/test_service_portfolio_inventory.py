from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db


def _seed_inventory(con):
    con.execute(
        """
        INSERT INTO assets(item_id, type_id, quantity, is_singleton, location_id, location_type, location_flag, updated)
        VALUES
          (1,1,5,0,60003760,'station','hangar','2024-01-01'),
          (2,2,3,0,60003760,'station','hangar','2024-01-01')
        """
    )
    con.execute(
        """
        INSERT INTO type_valuations(type_id, quicksell_bid, mark_ask, updated)
        VALUES (1,10,12,'2024-01-01'), (2,5,7,'2024-01-01')
        """
    )
    con.execute(
        """
        INSERT INTO types(type_id, name) VALUES (1,'Foo'), (2,'Bar')
        """
    )
    con.commit()


def test_inventory_basic(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_inventory(con)
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/portfolio/inventory", params={"sort": "type_id", "dir": "asc"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    first = items[0]
    assert first["type_id"] == 1
    assert first["type_name"] == "Foo"
    assert first["quantity"] == 5
    assert first["quicksell"] == 50.0
    assert first["mark"] == 60.0


def test_inventory_paging_and_search(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_inventory(con)
    finally:
        con.close()
    client = TestClient(service.app)
    resp = client.get("/portfolio/inventory", params={"limit": 1, "sort": "type_id", "dir": "asc"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["type_id"] == 1
    resp = client.get("/portfolio/inventory", params={"limit": 1, "offset": 1, "sort": "type_id", "dir": "asc"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["type_id"] == 2
    resp = client.get("/portfolio/inventory", params={"search": "Bar"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["type_id"] == 2
