from datetime import datetime
from .db import connect
from .config import STATION_ID, REGION_ID, SALES_TAX, BROKER_SELL
from .market import best_bid_ask_station


def refresh_type_valuations(con, type_ids):
    for tid in type_ids:
        bid, ask = best_bid_ask_station(tid, STATION_ID, REGION_ID)
        con.execute(
            """
            INSERT OR REPLACE INTO type_valuations (type_id, quicksell_bid, mark_ask, updated)
            VALUES (?,?,?,?)
            """,
            (tid, bid or 0.0, ask or 0.0, datetime.utcnow().isoformat()),
        )
    con.commit()


def compute_portfolio_snapshot(con):
    cur = con.cursor()
    bal = cur.execute(
        "SELECT balance FROM wallet_snapshots ORDER BY ts_utc DESC LIMIT 1"
    ).fetchone()
    balance = bal[0] if bal else 0.0

    row = cur.execute(
        """
        SELECT
          SUM(CASE WHEN is_buy=1 THEN COALESCE(escrow,0) ELSE 0 END),
          SUM(CASE WHEN is_buy=0 THEN price*volume_remain ELSE 0 END)
        FROM char_orders WHERE state='open'
        """
    ).fetchone()
    buy_escrow = row[0] or 0.0
    sell_gross = row[1] or 0.0

    inv = cur.execute(
        """
        SELECT a.type_id, SUM(a.quantity)
        FROM assets a
        GROUP BY a.type_id
        """
    ).fetchall()
    qs_val = mk_val = 0.0
    for tid, qty in inv:
        tv = cur.execute(
            "SELECT quicksell_bid, mark_ask FROM type_valuations WHERE type_id=?",
            (tid,),
        ).fetchone()
        if not tv:
            continue
        bid, ask = tv
        qs_val += (bid or 0.0) * qty
        mk_val += (ask or bid or 0.0) * qty

    sell_net = sell_gross * (1 - SALES_TAX - BROKER_SELL)

    nav_quicksell = balance + buy_escrow + qs_val + sell_net
    nav_mark = balance + buy_escrow + mk_val + sell_net

    day = datetime.utcnow().date().isoformat()
    con.execute(
        """
        INSERT OR REPLACE INTO portfolio_daily
          (day, wallet_balance, buy_escrow, sell_gross, inventory_quicksell, inventory_mark, nav_quicksell, nav_mark)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (day, balance, buy_escrow, sell_gross, qs_val, mk_val, nav_quicksell, nav_mark),
    )
    con.commit()
    return {
        "wallet_balance": balance,
        "buy_escrow": buy_escrow,
        "sell_gross": sell_gross,
        "inventory_quicksell": qs_val,
        "inventory_mark": mk_val,
        "nav_quicksell": nav_quicksell,
        "nav_mark": nav_mark,
    }
