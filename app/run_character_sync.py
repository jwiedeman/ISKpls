from .db import init_db, connect
from .char_sync import (
    sync_wallet_balance,
    sync_wallet_journal,
    sync_wallet_transactions,
    sync_open_orders,
    sync_order_history,
    sync_assets,
)
from .valuation import refresh_type_valuations, compute_portfolio_snapshot

CHAR_ID = 0  # replace with your character id
TOKEN = ""  # replace with access token


def main():
    con = init_db()
    sync_wallet_balance(con, CHAR_ID, TOKEN)
    sync_wallet_journal(con, CHAR_ID, TOKEN)
    sync_wallet_transactions(con, CHAR_ID, TOKEN)
    sync_open_orders(con, CHAR_ID, TOKEN)
    sync_order_history(con, CHAR_ID, TOKEN)
    sync_assets(con, CHAR_ID, TOKEN)
    cur = con.cursor()
    type_ids = set(
        t
        for (t,) in cur.execute(
            "SELECT DISTINCT type_id FROM assets UNION SELECT DISTINCT type_id FROM char_orders"
        )
    )
    if type_ids:
        refresh_type_valuations(con, sorted(type_ids))
    snap = compute_portfolio_snapshot(con)
    print("Portfolio:", snap)


if __name__ == "__main__":
    main()
