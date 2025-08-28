from datetime import datetime
import pathlib, sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app import db, scheduler
from app.config import STATION_ID


def _fake_refresh_one(con, tid):
    ts = datetime.utcnow().isoformat()
    con.execute(
        """
        INSERT OR REPLACE INTO market_snapshots
        (ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (ts, tid, STATION_ID, None, None, 0, 0, 0, 0),
    )
    con.execute(
        """
        UPDATE type_status SET last_orders_refresh=?, next_refresh=datetime('now', '+60 minutes')
        WHERE type_id=?
        """,
        (ts, tid),
    )


def test_scheduler_tick_emits_structured_events(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.init_db()
    con = db.connect()
    try:
        for tid, tier in [(1, "A"), (2, "B"), (3, "C")]:
            con.execute(
                "INSERT INTO type_status(type_id, tier, update_interval_min) VALUES (?,?,0)",
                (tid, tier),
            )
        con.commit()
    finally:
        con.close()

    events = []

    async def fake_broadcast(evt):
        events.append(evt)

    monkeypatch.setattr(scheduler, "refresh_one", _fake_refresh_one)
    monkeypatch.setattr("app.emit.broadcast", fake_broadcast)

    scheduler.run_tick(max_calls=10, workers=1)

    tick_events = [e for e in events if e.get("job") == "scheduler_tick"]

    start = next(e for e in tick_events if e.get("phase") == "start")
    assert start["tiers"] == {"A": 1, "B": 1, "C": 1, "D": 0}
    assert start["selected"] == 3

    progresses = [e for e in tick_events if e.get("phase") == "progress"]
    assert progresses[-1]["done"] == 3
    assert progresses[-1]["total"] == 3

    finish = next(e for e in tick_events if e.get("phase") == "finish")
    assert finish["items_written"] == 3
    assert finish["unique_types_touched"] == 3
    assert finish["errors"] == 0

