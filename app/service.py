from __future__ import annotations
from fastapi import FastAPI, HTTPException
from .settings_service import get_settings, update_settings
from .recommender import build_recommendations
from .scheduler import run_tick
from .db import connect
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
    return {"jobs": [{"name": n, "ts_utc": t, "ok": bool(o)} for n, t, o in rows]}


@app.get("/settings")
def read_settings():
    return get_settings()


@app.put("/settings")
def write_settings(settings: dict):
    allowed = set(get_settings().keys())
    for key in settings.keys():
        if key not in allowed:
            raise HTTPException(status_code=400, detail=f"Unknown setting {key}")
    update_settings(settings)
    return get_settings()


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


@app.post("/jobs/{name}/run")
def run_job(name: str):
    if name == "recommendations":
        recs = build_recommendations()
        return {"count": len(recs)}
    if name == "scheduler_tick":
        run_tick()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Job not found")
