from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app import type_cache


def _seed_types(con):
    con.execute(
        """
        INSERT INTO types(type_id, name, group_id)
        VALUES (1, 'Foo', 10), (2, 'Bar', 20)
        """
    )
    con.commit()


def test_types_map(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_types(con)
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/types/map", params={"ids": "1,2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["1"] == "Foo"
    assert data["2"] == "Bar"


def test_types_map_fetches_unknown_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    type_cache._type_name_cache = None

    def fake_fetch(ids):
        if 545 in ids:
            return {
                545: {
                    "name": "Widget",
                    "group_id": 10,
                    "category_id": 1,
                    "volume": 1.0,
                    "meta_level": None,
                    "market_group_id": None,
                }
            }
        return {}

    monkeypatch.setattr(type_cache, "_fetch_details_from_esi", fake_fetch)

    client = TestClient(service.app)
    resp = client.get("/types/map", params={"ids": "545"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["545"] == "Widget"

    # Ensure name was cached in the database
    con = db.connect()
    try:
        row = con.execute(
            "SELECT name FROM types WHERE type_id=545"
        ).fetchone()
    finally:
        con.close()
    assert row[0] == "Widget"
