from __future__ import annotations

"""Simple in-process job queue with basic rate limiting.

This module exposes two globals, ``JOB_QUEUE`` and ``IN_FLIGHT``, which are
used by the ``/status`` API for observability. Jobs can be enqueued with a
priority (``P0``..``P3``) and are executed in order by ``run_next_job`` or the
``worker`` loop. A lightweight rate limiter adapts to the ESI error limit
headers exposed via :mod:`app.esi`.
"""

from dataclasses import dataclass, field
from datetime import datetime
import heapq
import json
import time
import asyncio
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import db, esi
from .status import STATUS, emit


def _emit(evt: Dict[str, Any]) -> None:
    """Fire-and-forget wrapper around :func:`status.emit`.

    The job queue runs in synchronous contexts (including tests) where an
    event loop may not be running. If no loop is active we silently drop the
    event so unit tests remain simple.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(emit(evt))

# Public state for status reporting -------------------------------------------------

# Snapshot of queued job names for API consumers.
JOB_QUEUE: List[str] = []

# Information about the currently running job, if any.
IN_FLIGHT: Optional[Dict[str, str]] = None


# Internal priority queue ----------------------------------------------------------

_PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
_queue: List[Tuple[int, int, "Job"]] = []
_counter = 0


@dataclass
class Job:
    """A single unit of work to execute."""

    name: str
    func: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: str = "P2"


def _refresh_snapshot() -> None:
    """Update ``JOB_QUEUE`` snapshot from the internal priority queue."""
    JOB_QUEUE[:] = [job.name for _, _, job in sorted(_queue)]
    depth = queue_depth()
    STATUS["queue"] = depth
    _emit({"type": "queue", "depth": depth})


def enqueue(name: str, func: Callable[..., Any], priority: str = "P2", *args, **kwargs) -> None:
    """Enqueue a job for later execution."""

    global _counter
    prio = _PRIORITY.get(priority, 3)
    heapq.heappush(_queue, (prio, _counter, Job(name, func, args, kwargs, priority)))
    _counter += 1
    _refresh_snapshot()


def queue_depth() -> Dict[str, int]:
    """Return current queued job counts by priority class."""

    counts = {p: 0 for p in _PRIORITY.keys()}
    for _, _, job in _queue:
        counts[job.priority] += 1
    return counts


def run_next_job() -> bool:
    """Run the highest-priority job from the queue.

    Returns ``True`` if a job was executed, ``False`` if the queue was empty.
    """

    if not _queue:
        return False
    _, _, job = heapq.heappop(_queue)
    _refresh_snapshot()
    global IN_FLIGHT
    job_id = f"j-{uuid.uuid4().hex[:5]}"
    started = datetime.utcnow().isoformat()
    IN_FLIGHT = {"name": job.name, "id": job_id, "started": started}
    STATUS["inflight"] = [{"job": job.name, "id": job_id, "since": started}]
    _emit({"type": "job_started", "job": job.name, "id": job_id})
    t0 = time.time()
    ok = True
    try:
        job.func(*job.args, **job.kwargs)
    except Exception:  # pragma: no cover - propagated
        ok = False
        raise
    finally:
        ms = int((time.time() - t0) * 1000)
        _emit({"type": "job_finished", "id": job_id, "ok": ok, "ms": ms})
        IN_FLIGHT = None
        STATUS["inflight"] = []
    return True


def clear_queue() -> None:
    """Helper to clear internal state (primarily for tests)."""

    global _counter, IN_FLIGHT
    _queue.clear()
    JOB_QUEUE.clear()
    IN_FLIGHT = None
    _counter = 0


# Rate limiter ---------------------------------------------------------------------


class RateLimiter:
    """Token bucket limiter based on cached ESI error limit headers."""

    def allow(self) -> bool:
        """Return ``True`` if a call should be attempted now."""

        return esi.ERROR_LIMIT_REMAIN > 0

    def backoff(self) -> float:
        """Return suggested sleep time when the limiter is exhausted."""

        remain = esi.ERROR_LIMIT_REMAIN
        reset = esi.ERROR_LIMIT_RESET or 1
        if remain <= 0:
            # Sleep longer if we have exceeded the error budget.
            return reset / max(1, abs(remain))
        if remain < 20:
            return 1.0
        return 0.0


def worker(limiter: RateLimiter) -> None:
    """Continuously process queued jobs respecting the rate limiter."""

    while True:
        if _queue and limiter.allow():
            run_next_job()
        else:
            time.sleep(limiter.backoff())


# Job history recording ------------------------------------------------------------


def record_job(name: str, ok: bool, details: Optional[Any] = None) -> None:
    """Record a job execution in the ``jobs_history`` table."""

    con = db.connect()
    try:
        con.execute(
            """
            INSERT INTO jobs_history(name, ts_utc, ok, details_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                datetime.utcnow().isoformat(),
                1 if ok else 0,
                json.dumps(details) if details is not None else None,
            ),
        )
        con.commit()
    finally:
        con.close()

