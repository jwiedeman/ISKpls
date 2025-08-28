from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db
from app import type_cache
from app.config import STATION_ID


def _seed_recommendations(con):
    con.execute(
        """
        INSERT INTO recommendations(type_id, station_id, ts_utc, net_pct, uplift_mom, daily_capacity, rationale_json)
        VALUES
        (1, ?, '2024-01-01T00:00:00', 0.1, 0.25, 1000,
         '{"best_bid": 10.0, "best_ask": 12.0, "daily_volume": 500.0}'),
        (2, ?, '2024-01-02T00:00:00', 0.05, 0.30, 2000, '{}')
        """,
        (STATION_ID, STATION_ID),
    )
    con.commit()


def _seed_types(con):
    con.execute(
        """
        INSERT INTO types(type_id, name, group_id, category_id, meta_level)
        VALUES (1, 'Foo', 10, 6, 1), (2, 'Bar', 20, 7, 0)
        """
    )
    con.commit()


def _seed_trends(con):
    con.execute(
        """
        INSERT INTO type_trends(type_id, mom_pct, vol_30d_avg, vol_prev30_avg)
        VALUES (1, 0.25, 500, 400), (2, 0.30, 100, 80)
        """
    )
    con.commit()


def _seed_snapshots(con):
    con.execute(
        """
        INSERT INTO market_snapshots(ts_utc, type_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES
        ('2024-01-01T00:00:00',1,10,12,0,0,0,0),
        ('2024-01-01T00:00:00',2,11,13,0,0,0,0)
        """
    )
    con.commit()


def test_list_recommendations_filters(tmp_path, monkeypatch):
    # Redirect DB to temporary file and seed with sample data
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_types(con)
        _seed_trends(con)
        _seed_recommendations(con)
        _seed_snapshots(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/recommendations", params={"min_net": 0.08})
    assert resp.status_code == 200
    data = resp.json()
    # Only one record meets the net filter
    assert len(data["rows"]) == 1
    assert data["total"] == 1
    rec = data["rows"][0]
    assert rec["type_id"] == 1
    assert rec["type_name"] == "Foo"
    assert rec["station_id"] == STATION_ID
    assert rec["best_bid"] == 10.0
    assert rec["best_ask"] == 12.0
    assert rec["daily_volume"] == 500.0
    assert rec["snapshot_age_ms"] > 0

    # Filter by MoM uplift should exclude both when threshold high
    resp = client.get("/recommendations", params={"min_mom": 0.35})
    assert resp.status_code == 200
    assert resp.json()["rows"] == []

    # Filter by minimum volume using type_trends
    resp = client.get("/recommendations", params={"min_vol": 400})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) == 1
    assert data["total"] == 1
    assert data["rows"][0]["type_id"] == 1

    # Filter by category and meta level
    resp = client.get("/recommendations", params={"category": 6})
    assert resp.status_code == 200
    assert len(resp.json()["rows"]) == 1
    resp = client.get("/recommendations", params={"meta": 1})
    assert resp.status_code == 200
    assert len(resp.json()["rows"]) == 1


def test_recommendations_sort_and_offset(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_types(con)
        _seed_trends(con)
        _seed_recommendations(con)
        _seed_snapshots(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)

    # Sort ascending by net_pct should put type 2 first
    resp = client.get("/recommendations", params={"sort": "net_pct", "dir": "asc"})
    assert resp.status_code == 200
    data = resp.json()["rows"]
    assert data[0]["type_id"] == 2

    # Offset should skip the first record when ordered by ts_utc desc
    resp = client.get(
        "/recommendations",
        params={"limit": 1, "offset": 1, "sort": "ts_utc", "dir": "desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["type_id"] == 1


def test_recommendations_search(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        _seed_types(con)
        _seed_trends(con)
        _seed_recommendations(con)
        _seed_snapshots(con)
        type_cache.refresh_type_name_cache()
    finally:
        con.close()

    client = TestClient(service.app)
    resp = client.get("/recommendations", params={"search": "Foo"})
    assert resp.status_code == 200
    data = resp.json()["rows"]
    assert len(data) == 1
    assert data[0]["type_id"] == 1

    resp = client.get("/recommendations", params={"search": "2"})
    assert resp.status_code == 200
    data = resp.json()["rows"]
    assert len(data) == 1
    assert data[0]["type_id"] == 2

