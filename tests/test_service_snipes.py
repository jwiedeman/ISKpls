from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db, type_cache


def _seed_data(con):
    con.execute(
        """
        INSERT INTO types(type_id, name) VALUES (1, 'Foo'), (2, 'Bar')
        """
    )
    con.execute(
        """
        INSERT INTO market_snapshots(ts_utc, type_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES
          ('2024-01-01T00:00:00', 1, 100.0, 80.0, 1, 1, 10, 10),
          ('2024-01-01T00:00:00', 2, 100.0, 99.0, 1, 1, 10, 10)
        """
    )
    con.commit()


def test_snipes_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_data(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/snipes")
    assert resp.status_code == 200
    data = resp.json()
    snipes = data["snipes"]
    assert len(snipes) == 1
    s = snipes[0]
    assert s["type_id"] == 1
    assert s["type_name"] == "Foo"
    assert s["best_bid"] == 100.0
    assert s["best_ask"] == 80.0
    assert s["net_pct"] > 0
