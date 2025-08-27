import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import service, db, type_cache


def test_watchlist_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        con.execute(
            "INSERT INTO types(type_id, name, group_id) VALUES (42, 'Foo', 10)",
        )
        con.commit()
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)

    resp = client.get("/watchlist")
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    resp = client.post("/watchlist/42")
    assert resp.status_code == 200

    resp = client.get("/watchlist")
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["type_id"] == 42
    assert item["type_name"] == "Foo"

    resp = client.delete("/watchlist/42")
    assert resp.status_code == 200

    resp = client.get("/watchlist")
    assert resp.json()["items"] == []
