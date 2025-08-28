from fastapi import APIRouter, WebSocket
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Set

status_router = APIRouter()

# cache filled by scheduler
STATUS: Dict[str, Any] = {
    "inflight": [],
    "last_runs": [],
    "counts": {},
    "esi": {},
    "queue": {},
}
WS_CLIENTS: Set[WebSocket] = set()

# Internal heartbeat task reference so it can be cancelled on shutdown.
_heartbeat_task: Optional[asyncio.Task] = None

@status_router.get("/status")
def get_status() -> Dict[str, Any]:
    return STATUS

@status_router.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    WS_CLIENTS.add(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive
    except Exception:
        pass
    finally:
        WS_CLIENTS.discard(ws)

async def emit(evt: Dict[str, Any]) -> None:
    dead = []
    for ws in WS_CLIENTS:
        try:
            await ws.send_json(evt)
        except Exception:
            dead.append(ws)
    for ws in dead:
        WS_CLIENTS.discard(ws)


async def _heartbeat_loop(interval: float) -> None:
    """Background task that periodically emits heartbeat events."""
    try:
        while True:
            await asyncio.sleep(interval)
            now = datetime.utcnow().isoformat() + "Z"
            await emit({"type": "heartbeat", "now": now})
    except asyncio.CancelledError:  # pragma: no cover - task cancellation
        pass


def start_heartbeat(interval: float = 10.0) -> None:
    """Launch the heartbeat background task if an event loop is running."""
    global _heartbeat_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no loop running (e.g., during tests)
        return
    if _heartbeat_task is None or _heartbeat_task.done():
        _heartbeat_task = loop.create_task(_heartbeat_loop(interval))


def stop_heartbeat() -> None:
    """Cancel the heartbeat task if active."""
    global _heartbeat_task
    if _heartbeat_task is not None:
        _heartbeat_task.cancel()
        _heartbeat_task = None
