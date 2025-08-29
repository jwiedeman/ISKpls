import time
from .db import connect
from .config import REGION_ID, DATASOURCE, STATION_ID
from .esi import BASE, paged
from .util import utcnow


def fetch_snapshot(tid):
    """Return best prices and volume metrics for ``tid`` at Jita."""
    url = f"{BASE}/markets/{REGION_ID}/orders/"
    params = {"datasource": DATASOURCE, "order_type": "all", "type_id": tid}
    best_bid = best_ask = None
    bid_count = ask_count = 0
    bid_units = ask_units = 0
    for o in paged(url, params=params):
        if o.get("location_id") != STATION_ID:
            continue
        price = o["price"]
        vol = o["volume_remain"]
        if o.get("is_buy_order"):
            if best_bid is None or price > best_bid:
                best_bid = price
            bid_count += 1
            bid_units += vol
        else:
            if best_ask is None or price < best_ask:
                best_ask = price
            ask_count += 1
            ask_units += vol
    return best_bid, best_ask, bid_count, ask_count, bid_units, ask_units


def refresh_one(con, tid):
    bid, ask, bid_c, ask_c, bid_u, ask_u = fetch_snapshot(tid)
    ts = utcnow()
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
