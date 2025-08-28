from __future__ import annotations

from typing import List

from .db import connect
from .config import SPREAD_BUFFER, SNIPE_EPSILON
from .market import margin_after_fees
from .type_cache import get_type_name


def find_snipes(limit: int = 20, epsilon: float = SNIPE_EPSILON) -> List[dict]:
    """Return a list of underpriced sell orders worth sniping.

    A snipe is defined as a market snapshot where the best ask is priced very
    close to or below the best bid. Results are filtered to ensure the net
    margin after fees meets ``SPREAD_BUFFER``.
    """
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT m.type_id, m.best_bid, m.best_ask
            FROM market_snapshots m
            JOIN (
              SELECT type_id, MAX(ts_utc) AS ts
              FROM market_snapshots
              GROUP BY type_id
            ) latest
            ON latest.type_id = m.type_id AND latest.ts = m.ts_utc
            WHERE m.best_bid IS NOT NULL AND m.best_ask IS NOT NULL
            """
        ).fetchall()
    finally:
        con.close()

    results: List[dict] = []
    for type_id, bid, ask in rows:
        if ask > bid * (1 + epsilon):
            continue
        net = margin_after_fees(buy_px=ask, sell_px=bid)
        net_pct = net / ask if ask else 0.0
        if net_pct < SPREAD_BUFFER:
            continue
        results.append(
            {
                "type_id": type_id,
                "type_name": get_type_name(type_id),
                "best_bid": bid,
                "best_ask": ask,
                "net": net,
                "net_pct": net_pct,
            }
        )

    results.sort(key=lambda r: r["net_pct"], reverse=True)
    return results[:limit]
