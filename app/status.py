from fastapi import APIRouter, WebSocket
from typing import Any, Dict, Set

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
