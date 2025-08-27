from __future__ import annotations
from fastapi import FastAPI, HTTPException
from .settings_service import get_settings, update_settings, FIELD_META, validate_settings
from .recommender import build_recommendations
from .scheduler import run_tick
from .db import connect
from .valuation import compute_portfolio_snapshot
from .esi import get_error_limit_status
from .auth import get_token, token_status
import json

app = FastAPI()


@app.get("/status")
def status():
    """Return recent job history for health checks."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT name, ts_utc, ok FROM jobs_history ORDER BY ts_utc DESC LIMIT 20"
        ).fetchall()
    finally:
        con.close()
    return {
        "jobs": [{"name": n, "ts_utc": t, "ok": bool(o)} for n, t, o in rows],
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


@app.get("/types/map")
def types_map(ids: str | None = None):
    """Return mapping of type_ids to names.

    If ``ids`` query parameter is provided, it should be a comma-separated
    list of type IDs to look up. Otherwise all known types are returned.
    """
    con = connect()
    try:
        if ids:
            id_list = [int(i) for i in ids.split(",") if i]
            if id_list:
                placeholders = ",".join("?" for _ in id_list)
                rows = con.execute(
                    f"SELECT type_id, name FROM types WHERE type_id IN ({placeholders})",
                    id_list,
                ).fetchall()
            else:
                rows = []
        else:
            rows = con.execute("SELECT type_id, name FROM types").fetchall()
    finally:
        con.close()
    return {tid: name for tid, name in rows}


@app.get("/recommendations")
def list_recommendations(limit: int = 50, min_net: float = 0.0, min_mom: float = 0.0):
    """Return recent recommendations filtered by net spread and MoM uplift."""
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT type_id, ts_utc, net_pct, uplift_mom, daily_capacity, rationale_json
            FROM recommendations
            WHERE net_pct >= ? AND uplift_mom >= ?
            ORDER BY ts_utc DESC
            LIMIT ?
            """,
            (min_net, min_mom, limit),
        ).fetchall()
    finally:
        con.close()
    results = []
    for type_id, ts, net, mom, cap, rationale in rows:
        try:
            details = json.loads(rationale) if rationale else {}
        except json.JSONDecodeError:
            details = {}
        results.append(
            {
                "type_id": type_id,
                "ts_utc": ts,
                "net_pct": net,
                "uplift_mom": mom,
                "daily_capacity": cap,
                "details": details,
            }
        )
    return {"results": results}


@app.get("/orders/open")
def list_open_orders(limit: int = 100):
    """Return open character orders with fill percentage."""
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT order_id, is_buy, type_id, price, volume_total, volume_remain, issued, escrow
            FROM char_orders
            WHERE state='open'
            ORDER BY issued DESC
            LIMIT ?
            """,
            (limit,),
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
                "price": price,
                "volume_total": vol_total,
                "volume_remain": vol_remain,
                "fill_pct": fill_pct,
                "issued": issued,
                "escrow": escrow,
            }
        )
    return {"orders": orders}


@app.get("/orders/history")
def list_order_history(limit: int = 100):
    """Return recently closed character orders with fill percentage and state."""
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT order_id, is_buy, type_id, price, volume_total, volume_remain, issued, state, escrow
            FROM char_orders
            WHERE state != 'open'
            ORDER BY issued DESC
            LIMIT ?
            """,
            (limit,),
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


@app.get("/portfolio/nav")
def portfolio_nav():
    """Compute and return a portfolio NAV snapshot."""
    con = connect()
    try:
        snapshot = compute_portfolio_snapshot(con)
    finally:
        con.close()
    return snapshot


@app.post("/jobs/{name}/run")
def run_job(name: str):
    if name == "recommendations":
        recs = build_recommendations()
        return {"count": len(recs)}
    if name == "scheduler_tick":
        run_tick()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Job not found")
