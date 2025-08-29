import sqlite3
from .esi import BASE, paged
from .config import REGION_ID, DATASOURCE
from .db import connect
from .util import utcnow


def seed_region_types():
    con = connect()
    now = utcnow()
    url = f"{BASE}/markets/{REGION_ID}/types/"
    for tid in paged(url, params={"datasource": DATASOURCE}):
        con.execute(
            """
            INSERT INTO region_types(region_id, type_id, first_seen, last_seen)
            VALUES (?,?,?,?)
            ON CONFLICT(region_id, type_id) DO UPDATE SET last_seen=excluded.last_seen
            """,
            (REGION_ID, tid, now, now),
        )
        con.execute(
            """
            INSERT OR IGNORE INTO type_status(type_id, tier, update_interval_min)
            VALUES (?, 'C', 360)
            """,
            (tid,),
        )
    con.commit()
    con.close()
