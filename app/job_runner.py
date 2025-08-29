import os
import threading
from datetime import datetime, timedelta
from typing import Dict, Callable

from .jobs import enqueue, worker, RateLimiter, record_job
from .settings_service import get_scheduler_settings
from .run_character_sync import main as sync_character_main
from .trends import refresh_trends
from .scheduler import run_tick
from .recommender import build_recommendations
from .valuation import refresh_type_valuations
from .db import session, connect
from .util import utcnow_dt, parse_utc, utcnow
from .emit import pipeline_profit_updated

# Mapping of job names to callable wrappers ----------------------------------

def _job_sync_character() -> None:
    try:
        sync_character_main()
        record_job("sync_character", True)
    except Exception as exc:  # pragma: no cover - propagated
        record_job("sync_character", False, {"error": str(exc)})
        raise


def _job_refresh_trends() -> None:
    try:
        refresh_trends()
        record_job("refresh_trends", True)
    except Exception as exc:  # pragma: no cover - propagated
        record_job("refresh_trends", False, {"error": str(exc)})
        raise


def _job_snapshot_orders() -> None:
    try:
        run_tick()
        record_job("snapshot_orders", True)
    except Exception as exc:  # pragma: no cover - propagated
        record_job("snapshot_orders", False, {"error": str(exc)})
        raise


def _job_refresh_type_valuations() -> None:
    try:
        with session() as con:
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
        pipeline_profit_updated(count, utcnow())
        record_job("refresh_type_valuations", True, {"count": count})
    except Exception as exc:  # pragma: no cover - propagated
        record_job("refresh_type_valuations", False, {"error": str(exc)})
        raise


def _job_recommender_scan() -> None:
    try:
        recs = build_recommendations(mode="profit_only")
        record_job("recommender_scan", True, {"count": len(recs)})
    except Exception as exc:  # pragma: no cover - propagated
        record_job("recommender_scan", False, {"error": str(exc)})
        raise


JOB_FUNCS: Dict[str, Callable[[], None]] = {
    "sync_character": _job_sync_character,
    "refresh_trends": _job_refresh_trends,
    "snapshot_orders": _job_snapshot_orders,
    "refresh_type_valuations": _job_refresh_type_valuations,
    "recommender_scan": _job_recommender_scan,
    # allow old name used in tests/UI
    "recommendations": _job_recommender_scan,
}

# Background worker and scheduler threads -------------------------------------

_stop_scheduler = threading.Event()


def enqueue_job(name: str) -> None:
    func = JOB_FUNCS.get(name)
    if not func:
        raise KeyError(name)
    enqueue(name, func)


def _scheduler_loop() -> None:
    # load last run timestamps from history
    last_run: Dict[str, datetime] = {}
    con = connect()
    try:
        rows = con.execute(
            "SELECT name, MAX(ts_utc) FROM jobs_history GROUP BY name"
        ).fetchall()
    finally:
        con.close()
    for name, ts in rows:
        if ts:
            last_run[name] = parse_utc(ts)

    while not _stop_scheduler.is_set():
        cfg = get_scheduler_settings()
        now = utcnow_dt()
        for name, meta in cfg.items():
            if not meta.get("enabled"):
                continue
            interval = timedelta(minutes=int(meta.get("interval", 0)))
            lr = last_run.get(name)
            if lr is None or now - lr >= interval:
                if name in JOB_FUNCS:
                    enqueue_job(name)
                    last_run[name] = now
        _stop_scheduler.wait(1)


def start_background_jobs() -> None:
    if os.getenv("DISABLE_BACKGROUND_JOBS"):
        return
    threading.Thread(target=worker, args=(RateLimiter(),), daemon=True).start()
    threading.Thread(target=_scheduler_loop, daemon=True).start()


def stop_background_jobs() -> None:
    _stop_scheduler.set()

