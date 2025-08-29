import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import service, db, type_cache
import app.config as config
from datetime import timedelta
from app.util import utcnow_dt


def seed_basic(con):
    con.execute(
        """
        INSERT INTO types(type_id, name, group_id, category_id, meta_level)
        VALUES (1, 'Foo', 10, 6, 1), (2, 'Bar', 20, 6, 0)
        """
    )
    con.execute(
        """
        INSERT INTO market_snapshots(ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES
        ('2024-01-01 00:00:00',1,?,110,100,0,0,0,0),
        ('2024-01-01 00:00:00',2,?,100,220,0,0,0,0)
        """,
        (config.STATION_ID, config.STATION_ID),
    )
    con.execute(
        """
        INSERT INTO type_trends(type_id, mom_pct, vol_30d_avg, vol_prev30_avg)
        VALUES (1,0.2,500,400),(2,0.1,300,250)
        """
    )
    con.execute(
        """
        INSERT INTO recommendations(type_id, station_id, ts_utc)
        VALUES (1, ?, '2024-01-01 00:00:00')
        """,
        (config.STATION_ID,),
    )
    con.commit()


def test_db_items(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        seed_basic(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()
    client = TestClient(service.app)
    resp = client.get("/db/items")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    deals = {r["deal"] for r in data["rows"]}
    assert deals <= {"Great", "Good", "Neutral", "Bad"}
    profit_pcts = [r["profit_pct"] for r in data["rows"]]
    assert any(p < 0 for p in profit_pcts)
    assert any(p > 0 for p in profit_pcts)
    for row in data["rows"]:
        assert "last_updated" in row
        assert row["has_both_sides"] is True


def test_recommendations_show_all(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        seed_basic(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()
    client = TestClient(service.app)
    resp = client.get("/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["rows"][0]["type_id"] == 1
    assert data["rows"][0]["has_both_sides"] is True
    resp = client.get("/recommendations", params={"show_all": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert {r["type_id"] for r in data["rows"]} == {1, 2}
    assert all(r["has_both_sides"] for r in data["rows"])


def seed_legacy(con):
    now = utcnow_dt()
    stale = now - timedelta(hours=1)
    con.execute(
        """
        INSERT INTO types(type_id, name, group_id, category_id, meta_level)
        VALUES (1, 'Foo', 10, 6, 1), (2, 'Bar', 20, 6, 0)
        """
    )
    con.execute(
        """
        INSERT INTO market_snapshots(ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES
        (?,1,?,110,100,0,0,0,0),
        (?,2,?,220,200,0,0,0,0)
        """,
        (now.strftime("%Y-%m-%d %H:%M:%S"), config.STATION_ID, stale.strftime("%Y-%m-%d %H:%M:%S"), config.STATION_ID),
    )
    con.execute(
        """
        INSERT INTO type_trends(type_id, mom_pct, vol_30d_avg, vol_prev30_avg)
        VALUES (1,0.2,500,400),(2,0.05,50,40)
        """
    )
    con.commit()


def test_recommendations_legacy_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        seed_legacy(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()
    client = TestClient(service.app)
    resp = client.get("/recommendations", params={"show_all": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    resp = client.get(
        "/recommendations", params={"show_all": True, "mode": "legacy"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["rows"][0]["type_id"] == 1
    assert data["rows"][0]["has_both_sides"] is True
