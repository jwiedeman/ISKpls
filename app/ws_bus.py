from fastapi import APIRouter, WebSocket
import asyncio
import json
from datetime import datetime

router = APIRouter()
_clients: set[WebSocket] = set()
_history: list[dict] = []
HISTORY_MAX = 200


async def broadcast(evt: dict) -> None:
    """Send an event to all connected WebSocket clients and store history."""
    _history.append(evt)
    if len(_history) > HISTORY_MAX:
        _history.pop(0)
    dead = []
    for ws in list(_clients):
        try:
            await ws.send_text(json.dumps(evt))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


@router.websocket("/ws")
async def ws(ws: WebSocket):
    """WebSocket endpoint broadcasting structured events."""
    await ws.accept()
    _clients.add(ws)
    # hydrate late joiners with recent history
    for evt in _history[-40:]:
        await ws.send_text(json.dumps(evt))
    try:
        while True:
            # keepalive (we ignore any received data)
            await ws.receive_text()
    except Exception:
        pass
    finally:
        _clients.discard(ws)


_heartbeat_task: asyncio.Task | None = None


async def _heartbeat_loop() -> None:
    while True:
        await broadcast({"type": "heartbeat", "now": datetime.utcnow().isoformat() + "Z"})
        await asyncio.sleep(5)


def start_heartbeat() -> None:
    """Launch background heartbeat broadcaster."""
    global _heartbeat_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _heartbeat_task is None or _heartbeat_task.done():
        _heartbeat_task = loop.create_task(_heartbeat_loop())


def stop_heartbeat() -> None:
    """Stop heartbeat broadcaster if running."""
    global _heartbeat_task
    if _heartbeat_task is not None:
        _heartbeat_task.cancel()
        _heartbeat_task = None
