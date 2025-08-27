import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

from .db import connect


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
