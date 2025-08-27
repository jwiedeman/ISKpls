from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db


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
