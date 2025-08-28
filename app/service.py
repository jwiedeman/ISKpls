from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any
from .settings_service import get_settings, update_settings, FIELD_META, validate_settings
from .recommender import build_recommendations
from .scheduler import run_tick
from .db import connect, init_db
from .valuation import compute_portfolio_snapshot, refresh_type_valuations
from .esi import get_error_limit_status
from . import jobs
from .auth import get_token, token_status
from .scheduler_config import get_scheduler_settings, update_scheduler_settings
from .type_cache import get_type_name, refresh_type_name_cache, ensure_type_names
from .snipes import find_snipes
from .config import SNIPE_EPSILON, SNIPE_Z, SPREAD_BUFFER
from .market import margin_after_fees
from .ticks import tick
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload the type ID to name mapping."""
    refresh_type_name_cache()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



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


@app.get("/status")
def status():
    """Return scheduler queue state and recent job metrics."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT name, ts_utc, ok FROM jobs_history ORDER BY ts_utc DESC LIMIT 20"
        ).fetchall()
        counts = {
            "10m": con.execute(
                "SELECT COUNT(*) FROM jobs_history WHERE ts_utc >= datetime('now','-10 minutes')"
            ).fetchone()[0],
            "1h": con.execute(
                "SELECT COUNT(*) FROM jobs_history WHERE ts_utc >= datetime('now','-60 minutes')"
            ).fetchone()[0],
            "24h": con.execute(
                "SELECT COUNT(*) FROM jobs_history WHERE ts_utc >= datetime('now','-1440 minutes')"
            ).fetchone()[0],
        }
    finally:
        con.close()
    return {
        "jobs": [{"name": n, "ts_utc": t, "ok": bool(o)} for n, t, o in rows],
        "queue": list(jobs.JOB_QUEUE),
        "in_flight": jobs.IN_FLIGHT,
        "counts": counts,
        "esi": get_error_limit_status(),
    }


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


@app.get("/recommendations")
def list_recommendations(
    limit: int = 50,
    offset: int = 0,
    sort: str = "ts_utc",
    dir: str = "desc",
    min_net: float = 0.0,
    min_mom: float = 0.0,
    search: str | None = None,
):
    """Return recent recommendations filtered by net spread and MoM uplift."""
    allowed = {
        "ts_utc": "ts_utc",
        "net_pct": "net_pct",
        "uplift_mom": "uplift_mom",
        "daily_capacity": "daily_capacity",
    }
    col = allowed.get(sort, "ts_utc")
    direction = "ASC" if dir.lower() == "asc" else "DESC"
    where = ["net_pct >= ?", "uplift_mom >= ?"]
    params: list[Any] = [min_net, min_mom]
    join = ""
    if search:
        join = " JOIN types ON recommendations.type_id = types.type_id"
        if search.isdigit():
            where.append("(recommendations.type_id = ? OR types.name LIKE ?)")
            params.extend([int(search), f"%{search}%"])
        else:
            where.append("types.name LIKE ?")
            params.append(f"%{search}%")

    con = connect()
    try:
        rows = con.execute(
            f"""
            SELECT recommendations.type_id, station_id, ts_utc, net_pct, uplift_mom, daily_capacity, rationale_json
            FROM recommendations{join}
            WHERE {' AND '.join(where)}
            ORDER BY {col} {direction}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
    finally:
        con.close()
    results = []
    for type_id, station_id, ts, net, mom, cap, rationale in rows:
        try:
            details = json.loads(rationale) if rationale else {}
        except json.JSONDecodeError:
            details = {}
        results.append(
            {
                "type_id": type_id,
                "type_name": get_type_name(type_id),
                "station_id": station_id,
                "ts_utc": ts,
                "net_pct": net,
                "uplift_mom": mom,
                "daily_capacity": cap,
                "best_bid": details.get("best_bid"),
                "best_ask": details.get("best_ask"),
                "daily_volume": details.get("daily_volume"),
                "details": details,
            }
        )
    return {"results": results}


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
    join = ""
    where = ["state='open'"]
    params: list[Any] = []
    if search:
        join = " JOIN types ON char_orders.type_id = types.type_id"
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
            SELECT order_id, is_buy, char_orders.type_id, price, volume_total, volume_remain, issued, escrow
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
                "type_name": get_type_name(type_id),
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
            WHERE type_id=?
            ORDER BY ts_utc DESC
            LIMIT 1
            """,
            (type_id,),
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
    join = ""
    where = ["state != 'open'"]
    params: list[Any] = []
    if search:
        join = " JOIN types ON char_orders.type_id = types.type_id"
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
            SELECT order_id, is_buy, char_orders.type_id, price, volume_total, volume_remain, issued, state, escrow
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
                "type_name": get_type_name(type_id),
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


@app.post("/jobs/{name}/run")
def run_job(name: str):
    if name == "recommendations":
        recs = build_recommendations()
        return {"count": len(recs)}
    if name == "scheduler_tick":
        run_tick()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Job not found")
