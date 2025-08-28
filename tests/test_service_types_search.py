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
        """,
    )
    con.commit()


def test_types_search_by_name(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_types(con)
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/types/search", params={"q": "Foo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == [{"type_id": 1, "type_name": "Foo"}]


def test_types_search_by_id_fetches_unknown(tmp_path, monkeypatch):
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
    resp = client.get("/types/search", params={"q": "545"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == [{"type_id": 545, "type_name": "Widget"}]
