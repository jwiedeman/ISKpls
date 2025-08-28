from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter

status_router = APIRouter()

# Global snapshot for fallback polling -------------------------------------------------
STATUS: Dict[str, Any] = {
    "inflight": [],
    "last_runs": [],
    "esi": {},
    "queue": {},
    "logs": [],
    "counts": {},
}


def update_status(evt: Dict[str, Any]) -> None:
    """Update in-memory status snapshot based on an event."""
    t = evt.get("type")
    if t == "job_started":
        STATUS.setdefault("inflight", [])
        STATUS["inflight"].append(
            {
                "job": evt.get("job"),
                "runId": evt.get("runId"),
                "progress": 0,
                "detail": "",
                "since": datetime.utcnow().isoformat() + "Z",
            }
        )
    elif t == "job_progress":
        rid = evt.get("runId")
        for j in STATUS.get("inflight", []):
            if j.get("runId") == rid:
                j["progress"] = evt.get("progress", j.get("progress", 0))
                j["detail"] = evt.get("detail", "")
    elif t == "job_log":
        STATUS.setdefault("logs", [])
        STATUS["logs"].append(evt)
        if len(STATUS["logs"]) > 50:
            STATUS["logs"] = STATUS["logs"][-50:]
    elif t == "job_finished":
        rid = evt.get("runId")
        job_name = None
        remaining = []
        for j in STATUS.get("inflight", []):
            if j.get("runId") == rid:
                job_name = j.get("job")
            else:
                remaining.append(j)
        STATUS["inflight"] = remaining
        rec: Dict[str, Any] = {
            "job": job_name,
            "ok": evt.get("ok"),
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        if evt.get("ms") is not None:
            rec["ms"] = evt.get("ms")
        STATUS.setdefault("last_runs", [])
        STATUS["last_runs"] = [rec] + STATUS["last_runs"][-19:]
    elif t == "esi":
        STATUS["esi"] = {"remain": evt.get("remain"), "reset": evt.get("reset")}
    elif t == "queue":
        STATUS["queue"] = evt.get("depth", {})


@status_router.get("/status")
def get_status() -> Dict[str, Any]:
    """Return the current status snapshot for polling clients."""
    return {
        "inflight": STATUS.get("inflight", []),
        "last_runs": STATUS.get("last_runs", []),
        "esi": STATUS.get("esi", {}),
        "queue": STATUS.get("queue", {}),
        "logs": STATUS.get("logs", []),
        "counts": STATUS.get("counts", {}),
    }
