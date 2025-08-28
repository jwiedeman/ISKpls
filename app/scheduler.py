import time
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from .db import connect
from .jita_snapshots import refresh_one
from .jobs import record_job
from .status import emit_sync, STATUS

logger = logging.getLogger(__name__)


TIERS = {"A": 45, "B": 120, "C": 360, "D": 1440}


def classify_tier(vol):
    if vol >= 5000:
        return "A"
    if vol >= 1000:
        return "B"
    if vol >= 100:
        return "C"
    return "D"


def fill_queue_from_trends(max_types=1500):
    logger.info("Filling queue from trends")
    con = connect()
    rows = con.execute(
        "SELECT type_id, vol_30d_avg FROM type_trends ORDER BY vol_30d_avg DESC LIMIT ?",
        (max_types,),
    ).fetchall()
    for tid, v in rows:
        tier = classify_tier(v or 0)
        con.execute(
            """
            INSERT INTO type_status(type_id, tier, update_interval_min)
            VALUES (?,?,?)
            ON CONFLICT(type_id) DO UPDATE SET tier=excluded.tier, update_interval_min=excluded.update_interval_min
            """,
            (tid, tier, TIERS[tier]),
        )
    con.commit()
    con.close()
    logger.info("Queue filled for %s types", len(rows))


from . import esi

# track adaptive worker count to respect ESI error limits
_ADAPTIVE_WORKERS = 6


def _select_workers(target: int) -> int:
    """Adjust worker pool size based on cached ESI error limit headers."""
    global _ADAPTIVE_WORKERS
    remain = esi.ERROR_LIMIT_REMAIN
    if remain < 5 and _ADAPTIVE_WORKERS > 1:
        _ADAPTIVE_WORKERS -= 1
    elif remain > 80 and _ADAPTIVE_WORKERS < target:
        _ADAPTIVE_WORKERS += 1
    return min(target, _ADAPTIVE_WORKERS)


def run_tick(max_calls: int = 800, workers: int = 6) -> None:
    logger.info("Running scheduler tick")
    workers = _select_workers(workers)
    con = connect()
    try:
        due = con.execute(
            """
            SELECT type_id FROM type_status
            WHERE next_refresh IS NULL OR next_refresh <= datetime('now')
            ORDER BY COALESCE(last_orders_refresh,'1970-01-01') ASC
            LIMIT ?
            """,
            (max_calls,),
        ).fetchall()
    finally:
        con.close()

    count = len(due)
    logger.info("%s types due for refresh", count)
    job_id = f"j-{uuid.uuid4().hex[:5]}"
    emit_sync({"type": "job_started", "job": "scheduler_tick", "id": job_id, "meta": {"total": count}})

    t0 = time.time()
    lock = Lock()
    completed = 0

    def _run(tid: int) -> None:
        nonlocal completed
        c = connect()
        try:
            refresh_one(c, tid)
            c.commit()
        finally:
            c.close()
        with lock:
            completed += 1
            pct = int(completed / count * 100) if count else 100
            emit_sync({"type": "job_progress", "id": job_id, "progress": pct, "detail": f"type {tid}"})

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for (tid,) in due:
                pool.submit(_run, tid)
            pool.shutdown(wait=True)
        record_job("scheduler_tick", True, {"refreshed": count})
    except Exception as e:
        record_job("scheduler_tick", False, {"error": str(e)})
        emit_sync({"type": "job_finished", "id": job_id, "ok": False})
        raise
    else:
        ms = int((time.time() - t0) * 1000)
        # update recent type refresh counts for status snapshot
        con2 = connect()
        try:
            last10 = con2.execute(
                "SELECT COUNT(*) FROM type_status WHERE last_orders_refresh >= datetime('now', '-10 minutes')"
            ).fetchone()[0]
            last60 = con2.execute(
                "SELECT COUNT(*) FROM type_status WHERE last_orders_refresh >= datetime('now', '-60 minutes')"
            ).fetchone()[0]
        finally:
            con2.close()
        STATUS["counts"] = {"types_10m": last10, "types_1h": last60}
        emit_sync({"type": "counts", "counts": STATUS["counts"]})
        emit_sync({"type": "job_finished", "id": job_id, "ok": True, "items_written": count, "ms": ms})
