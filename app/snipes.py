from __future__ import annotations

from statistics import median, pstdev
from typing import List

from .db import connect
from .config import (
    SPREAD_BUFFER,
    SNIPE_DELTA,
    SNIPE_EPSILON,
    SNIPE_Z,
)
from .market import margin_after_fees
from .type_cache import get_type_name


def find_snipes(
    limit: int = 20,
    epsilon: float = SNIPE_EPSILON,
    min_net: float = SPREAD_BUFFER,
    z_thresh: float = SNIPE_Z,
) -> List[dict]:
    """Return a list of underpriced sell orders worth sniping.

    A snipe is defined as a market snapshot where the best ask is either priced
    very close to the best bid or is a strong negative anomaly compared to the
    recent ask history. An anomaly is flagged when the ask is at least
    ``SNIPE_DELTA`` below the rolling median and the z-score is below
    ``-z_thresh``. Results are filtered to ensure the net margin after fees
    meets ``min_net``.
    """
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT m.type_id, m.best_bid, m.best_ask, m.jita_ask_units
            FROM market_snapshots m
            JOIN (
              SELECT type_id, MAX(ts_utc) AS ts
              FROM market_snapshots
              GROUP BY type_id
            ) latest
            ON latest.type_id = m.type_id AND latest.ts = m.ts_utc
            WHERE m.best_bid IS NOT NULL AND m.best_ask IS NOT NULL
            """,
        ).fetchall()

        results: List[dict] = []
        for type_id, bid, ask, units in rows:
            hist = [
                a
                for (a,) in con.execute(
                    "SELECT best_ask FROM market_snapshots WHERE type_id=? ORDER BY ts_utc DESC LIMIT 20",
                    (type_id,),
                )
                if a is not None
            ]
            med = median(hist) if hist else None
            sd = pstdev(hist) if len(hist) > 1 else 0.0
            z = (ask - med) / sd if med is not None and sd > 0 else 0.0
            anomaly = bool(
                med is not None
                and ask <= med * (1 - SNIPE_DELTA)
                and z < -z_thresh
            )
            near_bid = ask <= bid * (1 + epsilon)
            if not (anomaly or near_bid):
                continue
            net = margin_after_fees(buy_px=ask, sell_px=bid)
            net_pct = net / ask if ask else 0.0
            if net_pct < min_net:
                continue
            results.append(
                {
                    "type_id": type_id,
                    "type_name": get_type_name(type_id),
                    "best_bid": bid,
                    "best_ask": ask,
                    "units": units,
                    "net": net,
                    "net_pct": net_pct,
                    "z_score": z,
                }
            )
    finally:
        con.close()

    results.sort(key=lambda r: r["net_pct"], reverse=True)
    return results[:limit]

