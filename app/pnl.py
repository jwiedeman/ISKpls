from collections import deque, defaultdict
from datetime import datetime
from .db import connect
from .util import utcnow


def load_transactions(con):
    return con.execute(
        """
        SELECT ts_utc, is_buy, type_id, quantity, unit_price, location_id, transaction_id, journal_ref_id
        FROM wallet_transactions ORDER BY ts_utc ASC
        """
    ).fetchall()


def load_journal(con):
    taxes = con.execute(
        "SELECT ts_utc, ABS(amount) FROM wallet_journal WHERE ref_type='transaction_tax' ORDER BY ts_utc"
    ).fetchall()
    brokers = con.execute(
        "SELECT ts_utc, ABS(amount) FROM wallet_journal WHERE ref_type='brokers_fee' ORDER BY ts_utc"
    ).fetchall()
    return taxes, brokers


def load_orders(con):
    return con.execute(
        "SELECT order_id, type_id, location_id, price, issued, volume_total FROM char_orders WHERE is_buy=0"
    ).fetchall()


def pnl_fifo():
    con = connect()
    tx = load_transactions(con)
    taxes, brokers = load_journal(con)
    orders = load_orders(con)

    broker_events = [(datetime.fromisoformat(t), fee) for t, fee in brokers]
    sell_orders = []
    for o in orders:
        sell_orders.append(
            {
                "order_id": o[0],
                "type_id": o[1],
                "location_id": o[2],
                "price": o[3],
                "issued": datetime.fromisoformat(o[4]),
                "vol_total": o[5],
                "vol_filled": 0,
                "broker_fee": 0.0,
            }
        )
    for t, fee in broker_events:
        candidates = [o for o in sell_orders if abs((o["issued"] - t).total_seconds()) <= 120]
        if candidates:
            o = min(candidates, key=lambda x: abs((x["issued"] - t).total_seconds()))
            o["broker_fee"] += fee

    tax_events = [(datetime.fromisoformat(t), tax) for t, tax in taxes]

    def nearest_tax(ts):
        if not tax_events:
            return 0.0
        candidates = [
            (abs((ts - tt).total_seconds()), tax)
            for tt, tax in tax_events
            if abs((ts - tt).total_seconds()) <= 5
        ]
        return min(candidates)[1] if candidates else 0.0

    inventory = defaultdict(deque)
    realized = []
    for ts_s, is_buy, type_id, qty, unit_price, loc, txid, jref in tx:
        ts = datetime.fromisoformat(ts_s)
        if is_buy:
            inventory[type_id].append([qty, unit_price])
        else:
            remaining = qty
            sell_gross = unit_price * qty
            sell_order_candidates = [
                o
                for o in sell_orders
                if o["type_id"] == type_id and o["location_id"] == loc and o["issued"] <= ts
            ]
            broker_alloc = 0.0
            if sell_order_candidates:
                o = min(sell_order_candidates, key=lambda x: abs((ts - x["issued"]).total_seconds()))
                portion = min(qty, o["vol_total"] - o["vol_filled"]) / max(1, o["vol_total"])
                broker_alloc = o["broker_fee"] * portion
                o["vol_filled"] += min(qty, o["vol_total"] - o["vol_filled"])
            tax = nearest_tax(ts)
            cost = 0.0
            while remaining > 0 and inventory[type_id]:
                lot = inventory[type_id][0]
                take = min(remaining, lot[0])
                cost += take * lot[1]
                lot[0] -= take
                remaining -= take
                if lot[0] == 0:
                    inventory[type_id].popleft()
            realized.append(
                (
                    f"{txid}",
                    ts_s,
                    type_id,
                    qty,
                    unit_price,
                    cost,
                    tax,
                    broker_alloc,
                    sell_gross - cost - tax - broker_alloc,
                )
            )
    for row in realized:
        con.execute(
            """
            INSERT OR REPLACE INTO realized_trades
              (trade_id, ts_utc, type_id, qty, sell_unit_price, cost_total, tax, broker_fee, pnl)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            row,
        )

    con.execute("DELETE FROM inventory_cost_basis")
    for type_id, lots in inventory.items():
        total_qty = sum(q for q, _ in lots)
        if total_qty > 0:
            avg_cost = sum(q * p for q, p in lots) / total_qty
            con.execute(
                """
                INSERT INTO inventory_cost_basis(type_id, remaining_qty, avg_cost, updated)
                VALUES (?,?,?,?)
                """,
                (type_id, total_qty, avg_cost, utcnow()),
            )
    con.commit()
    con.close()
    return realized
