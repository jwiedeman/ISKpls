import time
from .db import connect
from .jita_snapshots import refresh_one
from .trends import compute_mom, region_history
from .config import REGION_ID


TIERS = {"A": 90, "B": 240, "C": 360, "D": 1440}


def classify_tier(vol):
    if vol >= 5000:
        return "A"
    if vol >= 1000:
        return "B"
    if vol >= 100:
        return "C"
    return "D"


def fill_queue_from_trends(max_types=500):
    con = connect()
    rows = con.execute(
        "SELECT type_id, vol_30d_avg FROM type_trends ORDER BY vol_30d_avg DESC LIMIT ?",
        (max_types,),
    ).fetchall()
    for tid, v in rows:
        tier = classify_tier(v or 0)
        con.execute(
            """
            INSERT INTO type_status(type_id, tier, update_interval_min)
            VALUES (?,?,?)
            ON CONFLICT(type_id) DO UPDATE SET tier=excluded.tier, update_interval_min=excluded.update_interval_min
            """,
            (tid, tier, TIERS[tier]),
        )
    con.commit()
    con.close()


def run_tick(max_calls=200):
    con = connect()
    due = con.execute(
        """
        SELECT type_id FROM type_status
        WHERE next_refresh IS NULL OR next_refresh <= datetime('now')
        ORDER BY COALESCE(last_orders_refresh,'1970-01-01') ASC
        LIMIT ?
        """,
        (max_calls,),
    ).fetchall()
    for (tid,) in due:
        refresh_one(con, tid)
        con.commit()
        time.sleep(0.2)
    con.close()
