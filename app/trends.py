from datetime import datetime
from .db import connect
from .config import REGION_ID, DATASOURCE
from .esi import BASE
import requests


def region_history(tid):
    r = requests.get(
        f"{BASE}/markets/{REGION_ID}/history/",
        params={"type_id": tid, "datasource": DATASOURCE},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def compute_mom(hist):
    if len(hist) < 60:
        return None
    last30 = hist[-30:]
    prev30 = hist[-60:-30]
    m_now = sum(d["average"] for d in last30) / 30.0
    m_prev = sum(d["average"] for d in prev30) / 30.0
    v_now = sum(d["volume"] for d in last30) / 30.0
    v_prev = sum(d["volume"] for d in prev30) / 30.0
    return m_now / m_prev - 1.0, v_now, v_prev


def refresh_trends(limit_types=300):
    con = connect()
    rows = con.execute(
        "SELECT type_id FROM region_types WHERE region_id=? LIMIT ?",
        (REGION_ID, limit_types),
    ).fetchall()
    now = datetime.utcnow().isoformat()
    for (tid,) in rows:
        hist = region_history(tid)
        mom = compute_mom(hist)
        if mom:
            mom_pct, vnow, vprev = mom
            con.execute(
                """
                INSERT OR REPLACE INTO type_trends
                   (type_id, last_history_ts, mom_pct, vol_30d_avg, vol_prev30_avg)
                VALUES (?,?,?,?,?)
                """,
                (tid, now, mom_pct, vnow, vprev),
            )
    con.commit()
    con.close()
