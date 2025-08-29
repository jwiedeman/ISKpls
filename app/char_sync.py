import logging
from .esi import BASE, get, paged
from .db import connect
from .config import DATASOURCE
from .util import utcnow

logger = logging.getLogger(__name__)


def sync_wallet_balance(con, char_id, token):
    url = f"{BASE}/characters/{char_id}/wallet/"
    logger.info("Syncing wallet balance")
    data, hdrs, code = get(url, params={"datasource": DATASOURCE}, token=token)
    if code == 304:
        logger.info("Wallet balance not modified")
        return
    ts = utcnow()
    con.execute(
        "INSERT OR REPLACE INTO wallet_snapshots (ts_utc, balance) VALUES (?, ?)",
        (ts, float(data)),
    )
    con.commit()
    logger.info("Wallet balance updated")


def sync_wallet_journal(con, char_id, token, from_id=None):
    url = f"{BASE}/characters/{char_id}/wallet/journal/"
    params = {"datasource": DATASOURCE}
    while True:
        if from_id:
            params["from_id"] = from_id
        logger.info("Fetching wallet journal from_id=%s", from_id)
        data, hdrs, _ = get(url, params=params, token=token)
        if not data:
            logger.info("Wallet journal complete")
            break
        for row in data:
            con.execute(
                """
                INSERT OR IGNORE INTO wallet_journal
                  (id, ts_utc, amount, balance, ref_type, context_id, context_id_type, first_party_id, second_party_id, description)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["id"],
                    row["date"],
                    row.get("amount", 0.0),
                    row.get("balance"),
                    row.get("ref_type"),
                    row.get("context_id"),
                    row.get("context_id_type"),
                    row.get("first_party_id"),
                    row.get("second_party_id"),
                    row.get("description"),
                ),
            )
        con.commit()
        from_id = data[-1]["id"]


def sync_wallet_transactions(con, char_id, token, from_id=None):
    url = f"{BASE}/characters/{char_id}/wallet/transactions/"
    params = {"datasource": DATASOURCE}
    while True:
        if from_id:
            params["from_id"] = from_id
        logger.info("Fetching wallet transactions from_id=%s", from_id)
        data, hdrs, _ = get(url, params=params, token=token)
        if not data:
            logger.info("Wallet transactions complete")
            break
        for row in data:
            con.execute(
                """
                INSERT OR IGNORE INTO wallet_transactions
                  (transaction_id, ts_utc, client_id, location_id, type_id, quantity, unit_price, is_buy, journal_ref_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["transaction_id"],
                    row["date"],
                    row.get("client_id"),
                    row.get("location_id"),
                    row["type_id"],
                    row["quantity"],
                    row["unit_price"],
                    1 if row["is_buy"] else 0,
                    row.get("journal_ref_id"),
                ),
            )
        con.commit()
        from_id = data[-1]["transaction_id"]


def sync_open_orders(con, char_id, token):
    url = f"{BASE}/characters/{char_id}/orders/"
    orders = []
    logger.info("Fetching open orders")
    for o in paged(url, params={"datasource": DATASOURCE}, token=token):
        orders.append(o)
        con.execute(
            """
            INSERT OR REPLACE INTO char_orders
              (order_id, is_buy, region_id, location_id, type_id, price, volume_total, volume_remain, issued, duration, range, min_volume, escrow, last_seen, state)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open')
            """,
            (
                o["order_id"],
                1 if o["is_buy_order"] else 0,
                o.get("region_id"),
                o["location_id"],
                o["type_id"],
                o["price"],
                o["volume_total"],
                o["volume_remain"],
                o["issued"],
                o["duration"],
                o.get("range"),
                o.get("min_volume"),
                o.get("escrow", 0.0),
                utcnow(),
            ),
        )
    con.commit()
    con.execute(
        "UPDATE char_orders SET state='finished' WHERE state='open' AND last_seen < datetime('now','-2 hour')"
    )
    con.commit()
    logger.info("Open orders synced: %s orders", len(orders))


def sync_order_history(con, char_id, token, page_limit=10):
    url = f"{BASE}/characters/{char_id}/orders/history/"
    page = 1
    while page <= page_limit:
        logger.info("Fetching order history page %s", page)
        data, hdrs, _ = get(url, params={"datasource": DATASOURCE, "page": page}, token=token)
        if not data:
            logger.info("Order history complete")
            break
        for o in data:
            con.execute(
                """
                INSERT OR REPLACE INTO char_orders
                  (order_id, is_buy, region_id, location_id, type_id, price, volume_total, volume_remain, issued, duration, range, min_volume, escrow, last_seen, state)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    o["order_id"],
                    1 if o["is_buy_order"] else 0,
                    o.get("region_id"),
                    o["location_id"],
                    o["type_id"],
                    o["price"],
                    o["volume_total"],
                    o["volume_remain"],
                    o["issued"],
                    o["duration"],
                    o.get("range"),
                    o.get("min_volume"),
                    o.get("escrow", 0.0),
                    utcnow(),
                    o.get("state", "finished"),
                ),
            )
        con.commit()
        pages = int(hdrs.get("X-Pages", "1"))
        if page >= pages:
            break
        page += 1


def sync_assets(con, char_id, token):
    url = f"{BASE}/characters/{char_id}/assets/"
    logger.info("Fetching assets")
    count = 0
    for row in paged(url, params={"datasource": DATASOURCE}, token=token):
        con.execute(
            """
            INSERT OR REPLACE INTO assets
              (item_id, type_id, quantity, is_singleton, location_id, location_type, location_flag, updated)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                row["item_id"],
                row["type_id"],
                row["quantity"],
                1 if row.get("is_singleton") else 0,
                row["location_id"],
                row.get("location_type"),
                row.get("location_flag"),
                utcnow(),
            ),
        )
        count += 1
    con.commit()
    logger.info("Assets synced: %s", count)
