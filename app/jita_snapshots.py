import time
from datetime import datetime
import requests
from .db import connect
from .config import REGION_ID, DATASOURCE, STATION_ID
from .esi import BASE


def respect_error_limit(r):
    rem = int(r.headers.get("X-ESI-Error-Limit-Remain", "100"))
    rst = int(r.headers.get("X-ESI-Error-Limit-Reset", "10"))
    if rem < 5:
        time.sleep(max(rst, 2))


def fetch_orders_for_type(tid, order_type):
    url = f"{BASE}/markets/{REGION_ID}/orders/"
    best, count, units = (None, 0, 0)
    page = 1
    while True:
        params = {"order_type": order_type, "type_id": tid, "page": page, "datasource": DATASOURCE}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 304:
            break
        r.raise_for_status()
        data = r.json()
        for o in data:
            if o.get("location_id") != STATION_ID:
                continue
            if order_type == "buy":
                if best is None or o["price"] > best:
                    best = o["price"]
            else:
                if best is None or o["price"] < best:
                    best = o["price"]
            count += 1
            units += o["volume_remain"]
        pages = int(r.headers.get("X-Pages", "1"))
        respect_error_limit(r)
        if page >= pages:
            break
        page += 1
    return best, count, units


def refresh_one(con, tid):
    bid, bid_c, bid_u = fetch_orders_for_type(tid, "buy")
    ask, ask_c, ask_u = fetch_orders_for_type(tid, "sell")
    ts = datetime.utcnow().isoformat()
    con.execute(
        """
        INSERT OR REPLACE INTO market_snapshots
          (ts_utc, type_id, station_id, best_bid, best_ask, bid_count, ask_count, jita_bid_units, jita_ask_units)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (ts, tid, STATION_ID, bid, ask, bid_c, ask_c, bid_u, ask_u),
    )
    con.execute(
        """
        INSERT OR IGNORE INTO type_status(type_id)
        VALUES (?)
        """,
        (tid,),
    )
    con.execute(
        """
        UPDATE type_status SET last_orders_refresh=?, next_refresh=datetime('now', '+'||update_interval_min||' minutes')
        WHERE type_id=?
        """,
        (ts, tid),
    )


def refresh_batch(limit_types=150):
    con = connect()
    rows = con.execute(
        """
        SELECT t.type_id FROM region_types t
        LEFT JOIN type_status s ON s.type_id=t.type_id
        WHERE t.region_id=?
        ORDER BY COALESCE(s.last_orders_refresh,'1970-01-01') ASC
        LIMIT ?
        """,
        (REGION_ID, limit_types),
    ).fetchall()
    for (tid,) in rows:
        refresh_one(con, tid)
        con.commit()
        time.sleep(0.2)
    con.close()
