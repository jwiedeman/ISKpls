import time
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from .db import connect
from .jita_snapshots import refresh_one
from .jobs import record_job
from .status import STATUS
from .emit import job_started, job_progress, job_finished, emit_sync

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
    """Refresh due market snapshots and emit structured progress events."""

    logger.info("Running scheduler tick")
    workers = _select_workers(workers)

    con = connect()
    try:
        due = con.execute(
            """
            SELECT type_id, tier FROM type_status
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

    tier_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    for _, tier in due:
        if tier in tier_counts:
            tier_counts[tier] += 1

    rid = job_started("scheduler_tick", {"total": count})
    emit_sync(
        {
            "job": "scheduler_tick",
            "runId": rid,
            "phase": "start",
            "tiers": tier_counts,
            "selected": count,
            "workers": workers,
            "expected_pages": count,
        }
    )

    t0 = time.time()
    lock = Lock()
    completed = 0
    errors = 0

    def _run(tid: int) -> None:
        nonlocal completed, errors
        try:
            c = connect()
            try:
                refresh_one(c, tid)
                c.commit()
            finally:
                c.close()
        except Exception:
            errors += 1
        finally:
            with lock:
                completed += 1
                pct = int(completed / count * 100) if count else 100
                job_progress(rid, pct, f"type {tid}")
                emit_sync(
                    {
                        "job": "scheduler_tick",
                        "runId": rid,
                        "phase": "progress",
                        "done": completed,
                        "total": count,
                        "detail": f"type {tid}",
                    }
                )

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for tid, _ in due:
                pool.submit(_run, tid)
            pool.shutdown(wait=True)
        record_job("scheduler_tick", True, {"refreshed": count})
    except Exception as e:
        record_job("scheduler_tick", False, {"error": str(e)})
        emit_sync(
            {
                "job": "scheduler_tick",
                "runId": rid,
                "phase": "finish",
                "items_written": completed,
                "unique_types_touched": completed,
                "median_snapshot_age_ms": 0,
                "errors": errors or 1,
                "ms": int((time.time() - t0) * 1000),
            }
        )
        job_finished(rid, ok=False, error=str(e))
        raise
    else:
        ms = int((time.time() - t0) * 1000)
        con2 = connect()
        try:
            last10 = con2.execute(
                "SELECT COUNT(*) FROM type_status WHERE last_orders_refresh >= datetime('now', '-10 minutes')"
            ).fetchone()[0]
            last60 = con2.execute(
                "SELECT COUNT(*) FROM type_status WHERE last_orders_refresh >= datetime('now', '-60 minutes')"
            ).fetchone()[0]
            ages = [
                row[0]
                for row in con2.execute(
                    "SELECT (strftime('%s','now') - strftime('%s', last_orders_refresh)) * 1000 FROM type_status WHERE last_orders_refresh IS NOT NULL"
                ).fetchall()
            ]
        finally:
            con2.close()

        median_age = 0
        if ages:
            ages.sort()
            median_age = ages[len(ages) // 2]

        STATUS["counts"] = {"types_10m": last10, "types_1h": last60}
        emit_sync({"type": "counts", "counts": STATUS["counts"]})
        emit_sync(
            {
                "job": "scheduler_tick",
                "runId": rid,
                "phase": "finish",
                "items_written": completed,
                "unique_types_touched": completed,
                "median_snapshot_age_ms": median_age,
                "errors": errors,
                "ms": ms,
            }
        )
        job_finished(rid, ok=True, items=count, ms=ms)
