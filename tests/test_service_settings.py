from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import service, db  # noqa


def test_update_and_read_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    resp = client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "STATION_ID" in data

    resp = client.put("/settings", json={"STATION_ID": 1234})
    assert resp.status_code == 200
    assert resp.json()["STATION_ID"] == 1234


def test_reject_unknown_setting(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    resp = client.put("/settings", json={"NOT_A_SETTING": 1})
    assert resp.status_code == 400


def test_reject_out_of_range(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    resp = client.put("/settings", json={"SALES_TAX": -0.5})
    assert resp.status_code == 400


def test_reject_non_integer_id(tmp_path, monkeypatch):
    """Ensure integer-only fields reject float values."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    client = TestClient(service.app)

    resp = client.put("/settings", json={"STATION_ID": 123.45})
    assert resp.status_code == 400
