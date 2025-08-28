import asyncio
import time
from uuid import uuid4
from typing import Optional
from .ws_bus import broadcast
from . import status


def run_id() -> str:
    return f"run-{uuid4().hex[:8]}"


async def _send(evt: dict) -> None:
    status.update_status(evt)
    await broadcast(evt)


def emit_sync(evt: dict) -> None:
    """Best-effort helper to emit an event from sync code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_send(evt))
    else:
        loop.create_task(_send(evt))


# Job event helpers ------------------------------------------------------------------

def job_started(job: str, meta: Optional[dict] = None) -> str:
    rid = run_id()
    emit_sync({"type": "job_started", "job": job, "runId": rid, "meta": meta or {}})
    return rid


def job_progress(runId: str, progress: int, detail: str = "") -> None:
    emit_sync({"type": "job_progress", "runId": runId, "progress": progress, "detail": detail})


_last_log_ts = 0.0
_log_count = 0


def job_log(runId: str, level: str, message: str) -> None:
    """Emit log messages with simple backpressure to avoid floods."""
    global _last_log_ts, _log_count
    now = time.time()
    if now - _last_log_ts > 1.0:
        # new window
        _last_log_ts = now
        if _log_count > 5:
            emit_sync({"type": "job_log", "runId": runId, "level": level, "message": f"{_log_count} messages"})
        _log_count = 0
    _log_count += 1
    if _log_count <= 5:
        emit_sync({"type": "job_log", "runId": runId, "level": level, "message": message})


def job_finished(runId: str, ok: bool, items: int = 0, ms: int = 0, error: str | None = None) -> None:
    evt = {
        "type": "job_finished",
        "runId": runId,
        "ok": ok,
        "itemsWritten": items,
        "ms": ms,
        "error": error,
    }
    emit_sync(evt)


# Build events -----------------------------------------------------------------------

def build_started(job: str, meta: Optional[dict] = None) -> str:
    bid = run_id()
    emit_sync({"type": "build_started", "buildId": bid, "job": job, "meta": meta or {}})
    return bid


def build_progress(buildId: str, progress: int, stage: str = "", detail: str = "") -> None:
    emit_sync(
        {
            "type": "build_progress",
            "buildId": buildId,
            "progress": progress,
            "stage": stage,
            "detail": detail,
        }
    )


def build_finished(buildId: str, ok: bool, rows: int = 0, ms: int = 0, error: str | None = None) -> None:
    emit_sync(
        {
            "type": "build_finished",
            "buildId": buildId,
            "ok": ok,
            "rows": rows,
            "ms": ms,
            "error": error,
        }
    )
