import os
import logging

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
from .pnl import pnl_fifo
from .auth import get_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

CHAR_ID = int(os.getenv("CHAR_ID", "0"))


def main():
    token = get_token()
    con = init_db()
    logger = logging.getLogger(__name__)
    logger.info("Starting character sync for %s", CHAR_ID)
    sync_wallet_balance(con, CHAR_ID, token)
    sync_wallet_journal(con, CHAR_ID, token)
    sync_wallet_transactions(con, CHAR_ID, token)
    sync_open_orders(con, CHAR_ID, token)
    sync_order_history(con, CHAR_ID, token)
    sync_assets(con, CHAR_ID, token)
    pnl_fifo()
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
