from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Literal
from statistics import median
from .settings_service import (
    get_settings,
    update_settings,
    FIELD_META,
    validate_settings,
    get_scheduler_settings,
    update_scheduler_settings,
)
from .recommender import build_recommendations
from .scheduler import run_tick
from .db import connect, init_db
from .valuation import compute_portfolio_snapshot, refresh_type_valuations
from .auth import get_token, token_status
from .type_cache import get_type_name, refresh_type_name_cache, ensure_type_names
from .snipes import find_snipes
from .config import SNIPE_EPSILON, SNIPE_Z, SPREAD_BUFFER, STATION_ID, REC_FRESH_MS
from .market import margin_after_fees
from .ticks import tick
from .pricing import compute_profit, deal_label, Fees
from .status import status_router
from .ws_bus import router as ws_router, start_heartbeat, stop_heartbeat
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload the type ID to name mapping."""
    refresh_type_name_cache()
    start_heartbeat()
    try:
        yield
    finally:
        stop_heartbeat()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_router)
app.include_router(ws_router)



@app.on_event("startup")
def _startup() -> None:
    """Initialize the SQLite database and preload type names."""
    # Ensure the database schema exists before serving requests.
    init_db()
    # Warm the type ID → name cache for nicer API responses.
    refresh_type_name_cache()



@app.get("/healthz")
def healthz():
    """Simple liveness probe."""
    return {"status": "ok"}


@app.get("/auth/status")
def auth_status():
    """Report whether a cached SSO token is available."""
    return token_status()


@app.post("/auth/connect")
def auth_connect():
    """Initiate the SSO flow to obtain a token if missing or expired."""
    get_token()
    return {"status": "ok"}


@app.get("/settings")
def read_settings():
    return get_settings()


@app.put("/settings")
def write_settings(settings: dict):
    for key in settings.keys():
        if key not in FIELD_META:
            raise HTTPException(status_code=400, detail=f"Unknown setting {key}")
    try:
        validate_settings(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    update_settings(settings)
    return get_settings()


@app.get("/schedulers")
def read_schedulers():
    """Return scheduler job configuration."""
    return get_scheduler_settings()


@app.put("/schedulers")
def write_schedulers(settings: dict):
    """Update scheduler job configuration."""
    update_scheduler_settings(settings)
    return get_scheduler_settings()


@app.get("/types/map")
def types_map(ids: str | None = None):
    """Return mapping of type_ids to names.

    If ``ids`` query parameter is provided, it should be a comma-separated
    list of type IDs to look up. Otherwise all known types are returned.
    Unknown IDs are looked up via ESI and cached in the database.
    """
    if ids:
        id_list = [int(i) for i in ids.split(",") if i]
        return ensure_type_names(id_list)
    con = connect()
    try:
        rows = con.execute("SELECT type_id, name FROM types").fetchall()
    finally:
        con.close()
    return {tid: name for tid, name in rows}


@app.get("/types/search")
def search_types(q: str, limit: int = 20):
    """Search types by ID or name substring.

    ``q`` may be a type ID or part of a type name. Results include the
    resolved ``type_name`` for easier display on the client.
    """
    con = connect()
    try:
        if q.isdigit():
            tid = int(q)
            name = ensure_type_names([tid]).get(tid)
            results = []
            if name:
                results.append({"type_id": tid, "type_name": name})
            return {"results": results}
        rows = con.execute(
            "SELECT type_id, name FROM types WHERE name LIKE ? ORDER BY name LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
    finally:
        con.close()
    return {
        "results": [
            {"type_id": tid, "type_name": name} for tid, name in rows
        ]
    }


@app.get("/watchlist")
def get_watchlist():
    """Return all watchlisted type IDs with cached names."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT type_id, added_ts, note FROM watchlist ORDER BY added_ts DESC",
        ).fetchall()
    finally:
        con.close()
    return {
        "items": [
            {
                "type_id": tid,
                "type_name": get_type_name(tid),
                "added_ts": ts,
                "note": note,
            }
            for tid, ts, note in rows
        ]
    }


@app.post("/watchlist/{type_id}")
def add_watchlist(type_id: int, note: str | None = None):
    """Add a type to the watchlist."""
    con = connect()
    try:
        con.execute(
            "INSERT OR REPLACE INTO watchlist(type_id, added_ts, note) VALUES(?, ?, ?)",
            (type_id, datetime.utcnow().isoformat(), note),
        )
        con.commit()
    finally:
        con.close()
    return {"status": "ok"}


@app.delete("/watchlist/{type_id}")
def remove_watchlist(type_id: int):
    """Remove a type from the watchlist."""
    con = connect()
    try:
        con.execute("DELETE FROM watchlist WHERE type_id=?", (type_id,))
        con.commit()
    finally:
        con.close()
    return {"status": "ok"}


@app.get("/snipes")
def list_snipes(
    limit: int = 20,
    epsilon: float = SNIPE_EPSILON,
    min_net: float = SPREAD_BUFFER,
    z: float = SNIPE_Z,
):
    """Return potential underpriced sell orders for quick flips.

    ``epsilon`` controls how close the ask must be to the bid for instant flip
    candidates, ``min_net`` filters by minimum net percentage after fees, and
    ``z`` is the z-score threshold for anomaly detection.
    """
    return {
        "snipes": find_snipes(
            limit=limit, epsilon=epsilon, min_net=min_net, z_thresh=z
        )
    }


def _list_latest_items(
    *,
    station_id: int,
    limit: int,
    offset: int,
    sort: str,
    dir: str,
    search: str | None,
    min_profit_pct: float,
    deal_filter: set[str] | None = None,
    min_mom: float | None = None,
    min_vol: float | None = None,
    category: int | None = None,
    meta: int | None = None,
    show_all: bool = False,
    include_rec: bool = False,
    default_sort: str = "last_updated",
) -> dict[str, Any]:
    """Shared listing logic for latest price snapshots."""
    settings = get_settings()
    fees = Fees(
        buy_total=settings["BROKER_BUY"],
        sell_total=settings["SALES_TAX"]
        + settings["BROKER_SELL"]
        + settings["RELIST_HAIRCUT"],
    )
    thresholds = settings["DEAL_THRESHOLDS"]
    con = connect()
    try:
        where = ["lp.station_id = ?"]
        params: list[Any] = [station_id]
        if category is not None:
            where.append("types.category_id = ?")
            params.append(category)
        if meta is not None:
            where.append("COALESCE(types.meta_level,0) >= ?")
            params.append(meta)
        if search:
            if search.isdigit():
                where.append("(lp.type_id = ? OR types.name LIKE ?)")
                params.extend([int(search), f"%{search}%"])
            else:
                where.append("types.name LIKE ?")
                params.append(f"%{search}%")
        join_rec = ""
        select_extra = ""
        if include_rec:
            join_rec = "LEFT JOIN recommendations r ON r.type_id = lp.type_id AND r.station_id = ?"
            params.insert(0, station_id)
            if not show_all:
                where.append("r.type_id IS NOT NULL")
            select_extra = ", r.net_pct, r.uplift_mom, r.daily_capacity, r.rationale_json"
        where_clause = " AND ".join(where)
        rows = con.execute(
            f"""
            SELECT lp.type_id, types.name, lp.best_bid, lp.best_ask, lp.last_updated,
                   tr.mom_pct, tr.vol_30d_avg{select_extra}
            FROM latest_prices_v lp
            {join_rec}
            LEFT JOIN types ON lp.type_id = types.type_id
            LEFT JOIN type_trends tr ON tr.type_id = lp.type_id
            WHERE {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        con.close()
    now = datetime.utcnow()
    results = []
    for row in rows:
        if include_rec:
            (
                tid,
                tname,
                bid,
                ask,
                ts,
                mom,
                vol,
                net_pct,
                uplift_mom,
                daily_cap,
                rationale,
            ) = row
        else:
            tid, tname, bid, ask, ts, mom, vol = row
        has_both = bid is not None and ask is not None
        profit_isk, profit_pct = compute_profit(bid, ask, fees, tick)
        if profit_pct < min_profit_pct:
            continue
        if min_mom is not None and (mom is None or mom < min_mom):
            continue
        if min_vol is not None and (vol is None or vol < min_vol):
            continue
        label = deal_label(profit_pct, thresholds=thresholds)
        if deal_filter and label not in deal_filter:
            continue
        last_dt = datetime.fromisoformat(ts)
        fresh_ms = int((now - last_dt).total_seconds() * 1000)
        item = {
            "type_id": tid,
            "type_name": tname or get_type_name(tid),
            "best_bid": bid,
            "best_ask": ask,
            "last_updated": ts,
            "fresh_ms": fresh_ms,
            "profit_pct": profit_pct,
            "profit_isk": profit_isk,
            "deal": label,
            "mom": mom,
            "est_daily_vol": vol,
            "has_both_sides": has_both,
        }
        if include_rec:
            try:
                details = json.loads(rationale) if rationale else {}
            except json.JSONDecodeError:
                details = {}
            item.update(
                {
                    "net_pct": net_pct,
                    "uplift_mom": uplift_mom,
                    "daily_capacity": daily_cap,
                    "details": details,
                }
            )
        results.append(item)
    allowed = {
        "last_updated": "last_updated",
        "type_name": "type_name",
        "best_bid": "best_bid",
        "best_ask": "best_ask",
        "profit_pct": "profit_pct",
    }
    key = allowed.get(sort, default_sort)
    reverse = dir.lower() != "asc"
    results.sort(key=lambda r: (r[key] is None, r[key]), reverse=reverse)
    total = len(results)
    sliced = results[offset : offset + limit]
    return {"rows": sliced, "total": total}


@app.get("/db/items")
def list_db_items(
    station_id: int = STATION_ID,
    limit: int = 50,
    offset: int = 0,
    sort: str = "last_updated",
    dir: str = "desc",
    search: str | None = None,
    deal: list[str] | None = Query(None),
    min_profit_pct: float = 0.0,
):
    """Return latest known market data for all seen types."""
    deal_filter = {d.title() for d in (deal or [])}
    return _list_latest_items(
        station_id=station_id,
        limit=limit,
        offset=offset,
        sort=sort,
        dir=dir,
        search=search,
        min_profit_pct=min_profit_pct,
        deal_filter=deal_filter,
        default_sort="last_updated",
    )


def legacy_list_recommendations(
    limit: int,
    offset: int,
    sort: str,
    dir: str,
    min_profit_pct: float,
    min_mom: float,
    min_vol: float,
    category: int | None,
    meta: int | None,
    search: str | None,
    show_all: bool,
    station_id: int,
):
    """Return recommendations using legacy gating on freshness, MoM, and volume."""
    settings = get_settings()
    fees = Fees(
        buy_total=settings["BROKER_BUY"],
        sell_total=settings["SALES_TAX"]
        + settings["BROKER_SELL"]
        + settings["RELIST_HAIRCUT"],
    )
    thresholds = settings["DEAL_THRESHOLDS"]
    if min_mom == 0.0:
        min_mom = settings["MOM_THRESHOLD"]
    if min_vol == 0.0:
        min_vol = settings["MIN_DAILY_VOL"]
    con = connect()
    try:
        where: list[str] = ["lp.station_id = ?"]
        params: list[Any] = [station_id]
        if category is not None:
            where.append("types.category_id = ?")
            params.append(category)
        if meta is not None:
            where.append("COALESCE(types.meta_level,0) >= ?")
            params.append(meta)
        if search:
            if search.isdigit():
                where.append("(lp.type_id = ? OR types.name LIKE ?)")
                params.extend([int(search), f"%{search}%"])
            else:
                where.append("types.name LIKE ?")
                params.append(f"%{search}%")
        join_rec = "LEFT JOIN recommendations r ON r.type_id = lp.type_id AND r.station_id = ?"
        params.insert(0, station_id)
        if not show_all:
            where.append("r.type_id IS NOT NULL")
        where_clause = " AND ".join(where)
        rows = con.execute(
            f"""
            SELECT lp.type_id, types.name, lp.best_bid, lp.best_ask, lp.last_updated,
                   tr.mom_pct, tr.vol_30d_avg, r.net_pct, r.uplift_mom,
                   r.daily_capacity, r.rationale_json
            FROM latest_prices_v lp
            {join_rec}
            LEFT JOIN types ON lp.type_id = types.type_id
            LEFT JOIN type_trends tr ON tr.type_id = lp.type_id
            WHERE {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        con.close()
    now = datetime.utcnow()
    results = []
    for (
        tid,
        tname,
        bid,
        ask,
        ts,
        mom,
        vol,
        net_pct,
        uplift_mom,
        daily_cap,
        rationale,
    ) in rows:
        has_both = bid is not None and ask is not None
        profit_isk, profit_pct = compute_profit(bid, ask, fees, tick)
        if profit_pct < min_profit_pct:
            continue
        if mom is None or mom < min_mom:
            continue
        if vol is None or vol < min_vol:
            continue
        last_dt = datetime.fromisoformat(ts)
        fresh_ms = int((now - last_dt).total_seconds() * 1000)
        if fresh_ms > REC_FRESH_MS:
            continue
        label = deal_label(profit_pct, thresholds=thresholds)
        try:
            details = json.loads(rationale) if rationale else {}
        except json.JSONDecodeError:
            details = {}
        results.append(
            {
                "type_id": tid,
                "type_name": tname or get_type_name(tid),
                "best_bid": bid,
                "best_ask": ask,
                "last_updated": ts,
                "fresh_ms": fresh_ms,
                "profit_pct": profit_pct,
                "profit_isk": profit_isk,
                "deal": label,
                "mom": mom,
                "est_daily_vol": vol,
                "net_pct": net_pct,
                "uplift_mom": uplift_mom,
                "daily_capacity": daily_cap,
                "details": details,
                "has_both_sides": has_both,
            }
        )
    allowed = {
        "last_updated": "last_updated",
        "type_name": "type_name",
        "best_bid": "best_bid",
        "best_ask": "best_ask",
        "profit_pct": "profit_pct",
    }
    key = allowed.get(sort, "profit_pct")
    reverse = dir.lower() != "asc"
    results.sort(key=lambda r: (r[key] is None, r[key]), reverse=reverse)
    total = len(results)
    sliced = results[offset : offset + limit]
    return {"rows": sliced, "total": total}


@app.get("/recommendations")
def list_recommendations(
    limit: int = 50,
    offset: int = 0,
    sort: str = "profit_pct",
    dir: str = "desc",
    min_profit_pct: float = 0.0,
    min_mom: float | None = None,
    min_vol: float | None = None,
    category: int | None = None,
    meta: int | None = None,
    search: str | None = None,
    show_all: bool = False,
    mode: Literal["profit_only", "legacy"] = "profit_only",
    station_id: int = STATION_ID,
):
    if mode == "legacy":
        return legacy_list_recommendations(
            limit,
            offset,
            sort,
            dir,
            min_profit_pct,
            min_mom or 0.0,
            min_vol or 0.0,
            category,
            meta,
            search,
            show_all,
            station_id,
        )

    return _list_latest_items(
        station_id=station_id,
        limit=limit,
        offset=offset,
        sort=sort,
        dir=dir,
        search=search,
        min_profit_pct=min_profit_pct,
        min_mom=min_mom,
        min_vol=min_vol,
        category=category,
        meta=meta,
        show_all=show_all,
        include_rec=True,
        default_sort="profit_pct",
    )



@app.get("/orders/open")
def list_open_orders(
    limit: int = 100,
    offset: int = 0,
    sort: str = "issued",
    dir: str = "desc",
    search: str | None = None,
):
    """Return open character orders with fill percentage."""
    allowed = {"issued": "issued", "price": "price", "type_id": "type_id"}
    col = allowed.get(sort, "issued")
    direction = "ASC" if dir.lower() == "asc" else "DESC"
    join = " JOIN types ON char_orders.type_id = types.type_id"
    where = ["state='open'"]
    params: list[Any] = []
    if search:
        if search.isdigit():
            where.append("(char_orders.type_id = ? OR types.name LIKE ?)")
            params.extend([int(search), f"%{search}%"])
        else:
            where.append("types.name LIKE ?")
            params.append(f"%{search}%")
    con = connect()
    try:
        rows = con.execute(
            f"""
            SELECT order_id, is_buy, char_orders.type_id, types.name, price, volume_total, volume_remain, issued, escrow
            FROM char_orders{join}
            WHERE {' AND '.join(where)}
            ORDER BY {col} {direction}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
    finally:
        con.close()
    orders = []
    for (
        order_id,
        is_buy,
        type_id,
        type_name,
        price,
        vol_total,
        vol_remain,
        issued,
        escrow,
    ) in rows:
        fill_pct = (vol_total - vol_remain) / vol_total if vol_total else 0.0
        orders.append(
            {
                "order_id": order_id,
                "is_buy": bool(is_buy),
                "type_id": type_id,
                "type_name": type_name or get_type_name(type_id),
                "price": price,
                "volume_total": vol_total,
                "volume_remain": vol_remain,
                "fill_pct": fill_pct,
                "issued": issued,
                "escrow": escrow,
            }
        )
    return {"orders": orders}


@app.get("/orders/reprice")
def reprice_order(type_id: int):
    """Return one-tick reprice guidance and net margins for a type."""
    con = connect()
    try:
        row = con.execute(
            """
            SELECT best_bid, best_ask
            FROM market_snapshots
            WHERE type_id=? AND station_id=?
            ORDER BY ts_utc DESC
            LIMIT 1
            """,
            (type_id, STATION_ID),
        ).fetchone()
    finally:
        con.close()
    if not row or row[0] is None or row[1] is None:
        raise HTTPException(status_code=404, detail="No market data")
    best_bid, best_ask = row
    buy_price = tick(best_bid, "up")
    sell_price = tick(best_ask, "down")
    buy_net_pct = (
        margin_after_fees(buy_price, best_ask) / buy_price if buy_price else 0.0
    )
    sell_net_pct = (
        margin_after_fees(best_bid, sell_price) / best_bid if best_bid else 0.0
    )
    return {
        "type_id": type_id,
        "type_name": get_type_name(type_id),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "buy_net_pct": buy_net_pct,
        "sell_net_pct": sell_net_pct,
    }


@app.get("/orders/history")
def list_order_history(
    limit: int = 100,
    offset: int = 0,
    sort: str = "issued",
    dir: str = "desc",
    search: str | None = None,
):
    """Return recently closed character orders with fill percentage and state."""
    allowed = {"issued": "issued", "price": "price", "type_id": "type_id"}
    col = allowed.get(sort, "issued")
    direction = "ASC" if dir.lower() == "asc" else "DESC"
    join = " JOIN types ON char_orders.type_id = types.type_id"
    where = ["state != 'open'"]
    params: list[Any] = []
    if search:
        if search.isdigit():
            where.append("(char_orders.type_id = ? OR types.name LIKE ?)")
            params.extend([int(search), f"%{search}%"])
        else:
            where.append("types.name LIKE ?")
            params.append(f"%{search}%")
    con = connect()
    try:
        rows = con.execute(
            f"""
            SELECT order_id, is_buy, char_orders.type_id, types.name, price, volume_total, volume_remain, issued, state, escrow
            FROM char_orders{join}
            WHERE {' AND '.join(where)}
            ORDER BY {col} {direction}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
    finally:
        con.close()
    orders = []
    for (
        order_id,
        is_buy,
        type_id,
        type_name,
        price,
        vol_total,
        vol_remain,
        issued,
        state,
        escrow,
    ) in rows:
        fill_pct = (vol_total - vol_remain) / vol_total if vol_total else 0.0
        orders.append(
            {
                "order_id": order_id,
                "is_buy": bool(is_buy),
                "type_id": type_id,
                "type_name": type_name or get_type_name(type_id),
                "price": price,
                "volume_total": vol_total,
                "volume_remain": vol_remain,
                "fill_pct": fill_pct,
                "issued": issued,
                "state": state,
                "escrow": escrow,
            }
        )
    return {"orders": orders}


@app.get("/portfolio/inventory")
def list_inventory(
    limit: int = 100,
    offset: int = 0,
    sort: str = "mark",
    dir: str = "desc",
    search: str | None = None,
):
    """Return aggregated inventory positions with valuations."""
    allowed = {
        "type_id": "a.type_id",
        "quantity": "qty",
        "quicksell": "qs_value",
        "mark": "mk_value",
    }
    col = allowed.get(sort, "mk_value")
    direction = "ASC" if dir.lower() == "asc" else "DESC"
    con = connect()
    try:
        where = ""
        params: list[Any] = []
        if search:
            try:
                tid = int(search)
                where = "WHERE a.type_id=?"
                params.append(tid)
            except ValueError:
                where = "WHERE t.name LIKE ?"
                params.append(f"%{search}%")
        rows = con.execute(
            f"""
            SELECT a.type_id, t.name, SUM(a.quantity) AS qty,
                   SUM(a.quantity * COALESCE(v.quicksell_bid,0)) AS qs_value,
                   SUM(a.quantity * COALESCE(v.mark_ask, v.quicksell_bid,0)) AS mk_value
            FROM assets a
            LEFT JOIN types t ON t.type_id=a.type_id
            LEFT JOIN type_valuations v ON v.type_id=a.type_id
            {where}
            GROUP BY a.type_id, t.name
            ORDER BY {col} {direction}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
    finally:
        con.close()
    items = []
    for type_id, name, qty, qs_val, mk_val in rows:
        items.append(
            {
                "type_id": type_id,
                "type_name": name or get_type_name(type_id),
                "quantity": qty,
                "quicksell": qs_val,
                "mark": mk_val,
            }
        )
    return {"items": items}


@app.get("/inventory/coverage")
def inventory_coverage():
    """Return snapshot coverage statistics for market data."""
    con = connect()
    try:
        cur = con.cursor()
        types_indexed = cur.execute(
            "SELECT COUNT(DISTINCT type_id) FROM market_snapshots WHERE station_id=?",
            (STATION_ID,),
        ).fetchone()[0]
        books_last_10m = cur.execute(
            "SELECT COUNT(*) FROM market_snapshots WHERE station_id=? AND ts_utc >= datetime('now','-10 minutes')",
            (STATION_ID,),
        ).fetchone()[0]
        rows = cur.execute(
            "SELECT type_id, MAX(ts_utc) FROM market_snapshots WHERE station_id=? GROUP BY type_id",
            (STATION_ID,),
        ).fetchall()
    finally:
        con.close()

    now = datetime.utcnow()
    ages: list[int] = []
    oldest_type: int | None = None
    oldest_age = -1
    for type_id, ts in rows:
        if not ts:
            continue
        age = int((now - datetime.fromisoformat(ts)).total_seconds() * 1000)
        ages.append(age)
        if age > oldest_age:
            oldest_age = age
            oldest_type = type_id
    median_age = int(median(ages)) if ages else 0
    oldest_snapshot = (
        {"type_id": oldest_type, "age_ms": oldest_age} if oldest_type is not None else None
    )

    return {
        "station_id": STATION_ID,
        "types_indexed": types_indexed or 0,
        "books_last_10m": books_last_10m or 0,
        "median_snapshot_age_ms": median_age,
        "oldest_snapshot": oldest_snapshot,
    }


@app.get("/coverage")
def coverage_summary():
    """Return high level coverage metrics for market snapshots."""
    con = connect()
    try:
        cur = con.cursor()
        types_indexed = cur.execute(
            "SELECT COUNT(DISTINCT type_id) FROM market_snapshots WHERE station_id=?",
            (STATION_ID,),
        ).fetchone()[0]
        books_10m = cur.execute(
            "SELECT COUNT(*) FROM market_snapshots WHERE station_id=? AND ts_utc >= datetime('now','-10 minutes')",
            (STATION_ID,),
        ).fetchone()[0]
        distinct_24h = cur.execute(
            "SELECT COUNT(DISTINCT type_id) FROM market_snapshots WHERE station_id=? AND ts_utc >= datetime('now','-1 day')",
            (STATION_ID,),
        ).fetchone()[0]
        rows = cur.execute(
            "SELECT MAX(ts_utc) FROM market_snapshots WHERE station_id=? GROUP BY type_id",
            (STATION_ID,),
        ).fetchall()
    finally:
        con.close()

    now = datetime.utcnow()
    ages = [
        int((now - datetime.fromisoformat(ts)).total_seconds() * 1000)
        for (ts,) in rows
        if ts
    ]
    median_age_s = int(median(ages) / 1000) if ages else 0

    return {
        "types_indexed": types_indexed or 0,
        "books_10m": books_10m or 0,
        "median_age_s": median_age_s,
        "distinct_types_24h": distinct_24h or 0,
    }


@app.get("/portfolio/summary")
def portfolio_summary(basis: Literal["mark", "quicksell"] = "mark"):
    """Return aggregate portfolio metrics and recent realized PnL."""
    con = connect()
    try:
        snap = compute_portfolio_snapshot(con)
        cur = con.cursor()
        realized_7d = (
            cur.execute(
                "SELECT COALESCE(SUM(pnl),0) FROM realized_trades WHERE ts_utc >= datetime('now','-7 days')"
            ).fetchone()[0]
            or 0.0
        )
        realized_30d = (
            cur.execute(
                "SELECT COALESCE(SUM(pnl),0) FROM realized_trades WHERE ts_utc >= datetime('now','-30 days')"
            ).fetchone()[0]
            or 0.0
        )
    finally:
        con.close()

    sell_value_quicksell = snap["nav_quicksell"] - snap["wallet_balance"] - snap["buy_escrow"]
    sell_value_mark = snap["nav_mark"] - snap["wallet_balance"] - snap["buy_escrow"]

    return {
        "liquid": snap["wallet_balance"],
        "buy_escrow": snap["buy_escrow"],
        "sell_value_quicksell": sell_value_quicksell,
        "sell_value_mark": sell_value_mark,
        "nav_quicksell": snap["nav_quicksell"],
        "nav_mark": snap["nav_mark"],
        "realized_7d": realized_7d,
        "realized_30d": realized_30d,
        "basis": basis,
    }


@app.get("/portfolio/nav")
def portfolio_nav():
    """Compute and return a portfolio NAV snapshot."""
    con = connect()
    try:
        snapshot = compute_portfolio_snapshot(con)
    finally:
        con.close()
    return snapshot


@app.post("/valuations/recompute")
def recompute_valuations():
    """Refresh type valuations for all known assets and orders."""
    con = connect()
    try:
        cur = con.cursor()
        ids = [
            tid
            for (tid,) in cur.execute(
                "SELECT DISTINCT type_id FROM assets UNION SELECT DISTINCT type_id FROM char_orders"
            )
        ]
        if ids:
            refresh_type_valuations(con, sorted(ids))
        count = len(ids)
    finally:
        con.close()
    return {"count": count}


@app.post("/recommendations/build")
def recommendations_build(
    dry_run: bool = False,
    verbose: bool = False,
    mode: Literal["profit_only", "legacy"] = "profit_only",
):
    """Trigger a recommendations build or return dry-run counts."""
    res = build_recommendations(verbose=verbose, dry_run=dry_run, mode=mode)
    if dry_run:
        return res
    return {"rows": len(res)}


@app.post("/jobs/{name}/run")
def run_job(
    name: str,
    verbose: bool = False,
    mode: Literal["profit_only", "legacy"] = "profit_only",
):
    """Run a background job immediately.

    The optional ``verbose`` flag triggers additional event chatter so that
    testers can observe progress updates even in fast unit-test scenarios.
    """

    if name == "recommendations":
        recs = build_recommendations(verbose=verbose, mode=mode)
        return {"count": len(recs)}
    if name == "scheduler_tick":
        run_tick()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Job not found")
