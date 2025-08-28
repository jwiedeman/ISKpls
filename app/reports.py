import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

from .db import connect
from .config import STATION_ID


def items_summary(limit=50):
    """Return a DataFrame of item status with last update and unrealized P/L."""
    con = connect()
    df = pd.read_sql_query(
        """
        SELECT
          s.type_id,
          s.ts_utc AS last_updated,
          s.best_bid,
          s.best_ask,
          t.mom_pct,
          h.qty AS inv_qty,
          cb.avg_cost,
          (s.best_bid - cb.avg_cost) * COALESCE(h.qty,0) AS unrealized_pnl,
          CASE WHEN s.best_bid IS NOT NULL AND s.best_ask IS NOT NULL AND s.best_bid > 0
               THEN (s.best_ask - s.best_bid) / s.best_bid END AS spread_pct
        FROM (
            SELECT ms.* FROM market_snapshots ms
            JOIN (
              SELECT type_id, MAX(ts_utc) AS max_ts FROM market_snapshots WHERE station_id=? GROUP BY type_id
            ) latest ON ms.type_id = latest.type_id AND ms.ts_utc = latest.max_ts AND ms.station_id = ?
        ) s
        LEFT JOIN type_trends t ON t.type_id = s.type_id
        LEFT JOIN (
            SELECT type_id, SUM(quantity) AS qty FROM assets GROUP BY type_id
        ) h ON h.type_id = s.type_id
        LEFT JOIN inventory_cost_basis cb ON cb.type_id = s.type_id
        ORDER BY s.ts_utc DESC
        LIMIT ?
        """,
        con,
        params=(STATION_ID, STATION_ID, limit),
    )
    con.close()
    return df


def plot_realized_pnl_daily(savepath="realized_pnl_daily.png"):
    con = connect()
    df = pd.read_sql_query(
        """
        SELECT date(ts_utc) AS d, SUM(pnl) AS pnl
        FROM realized_trades
        GROUP BY date(ts_utc)
        ORDER BY d
        """,
        con,
    )
    con.close()
    if df.empty:
        print("No realized trades yet.")
        return
    plt.figure()
    plt.plot(df["d"], df["pnl"])
    plt.title("Realized P/L per day")
    plt.xlabel("Day")
    plt.ylabel("ISK")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(savepath)
    print(f"Saved {savepath}")


def plot_nav(savepath="nav_quicksell.png"):
    con = connect()
    df = pd.read_sql_query(
        """
        SELECT day, nav_quicksell FROM portfolio_daily ORDER BY day
        """,
        con,
    )
    con.close()
    if df.empty:
        print("No snapshots yet.")
        return
    plt.figure()
    plt.plot(df["day"], df["nav_quicksell"])
    plt.title("NAV (quicksell)")
    plt.xlabel("Day")
    plt.ylabel("ISK")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(savepath)
    print(f"Saved {savepath}")
