from datetime import datetime
import pandas as pd
from .esi import BASE, paged, get
from .config import (
    STATION_ID,
    REGION_ID,
    DATASOURCE,
    SALES_TAX,
    BROKER_SELL,
    BROKER_BUY,
    RELIST_HAIRCUT,
    MIN_DAYS_TRADED,
    VENUE,
)


def station_region_id(station_id):
    data, _, _ = get(
        f"{BASE}/universe/stations/{station_id}/", params={"datasource": DATASOURCE}
    )
    sys_id = data["system_id"]
    sys, _, _ = get(
        f"{BASE}/universe/systems/{sys_id}/", params={"datasource": DATASOURCE}
    )
    return sys["region_id"]


def best_bid_ask_station(type_id, station_id, region_id):
    url = f"{BASE}/markets/{region_id}/orders/"
    params = {"datasource": DATASOURCE, "order_type": "all", "type_id": type_id}
    buys, sells = [], []
    for o in paged(url, params=params):
        if o.get("location_id") != station_id:
            continue
        (buys if o["is_buy_order"] else sells).append(o)
    best_bid = max((b["price"] for b in buys), default=None)
    best_ask = min((s["price"] for s in sells), default=None)
    return best_bid, best_ask


def region_history(type_id, region_id):
    url = f"{BASE}/markets/{region_id}/history/"
    data, _, _ = get(url, params={"datasource": DATASOURCE, "type_id": type_id})
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df


def margin_after_fees(buy_px, sell_px):
    return sell_px * (1 - SALES_TAX - BROKER_SELL - RELIST_HAIRCUT) - buy_px * (
        1 + BROKER_BUY
    )


def mom_uplift(df):
    if len(df) < 60:
        return None
    last30 = df.tail(30)
    prev30 = df.iloc[-60:-30]
    if (last30["order_count"] > 0).sum() < MIN_DAYS_TRADED:
        return None
    if (prev30["order_count"] > 0).sum() < MIN_DAYS_TRADED:
        return None
    m_now = last30["average"].mean()
    m_prev = prev30["average"].mean()
    return (m_now / m_prev) - 1.0


def evaluate_type(type_id):
    reg_id = REGION_ID if REGION_ID else station_region_id(STATION_ID)
    df = region_history(type_id, reg_id)
    if df.empty:
        return None
    uplift = mom_uplift(df)
    bid, ask = best_bid_ask_station(type_id, STATION_ID, reg_id)
    if bid is None or ask is None:
        return None
    net = margin_after_fees(buy_px=bid, sell_px=ask)
    if bid == 0:
        return None
    net_pct = net / bid
    # Gate only on positive profit after fees
    if net_pct <= 0:
        return None
    daily_vol = df.tail(30)["volume"].mean() if len(df) else 0.0
    avg_series = df.tail(7)["average"] if len(df) else []
    daily_isk = daily_vol * (avg_series.mean() if len(avg_series) else 0.0)
    return {
        "type_id": type_id,
        "uplift_mom": uplift,
        "net_spread_pct": net_pct,
        "daily_isk_capacity": daily_isk,
        "daily_volume": daily_vol,
        "best_bid": bid,
        "best_ask": ask,
    }
