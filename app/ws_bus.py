from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio
import json
import logging
from contextlib import suppress
import inspect
from typing import Any, Dict
from .util import utcnow
from .status import update_status

router = APIRouter()
_clients: set[WebSocket] = set()
_history: list[Dict[str, Any]] = []
HISTORY_MAX = 200


async def broadcast(evt: Dict[str, Any]) -> None:
    """Send an event to all WebSocket clients and update status/history."""
    update_status(evt)
    _history.append(evt)
    if len(_history) > HISTORY_MAX:
        _history.pop(0)

    # ``evt`` may occasionally contain objects like ``datetime`` which are not
    # JSON serialisable by default. ``default=str`` provides a best-effort
    # coercion to string ensuring that the broadcast never raises because of
    # such values. This keeps the websocket pipeline resilient to unexpected
    # payloads while still logging them for debugging.
    msg = json.dumps(evt, default=str)
    dead: list[WebSocket] = []
    for ws in list(_clients):
        try:
            await ws.send_text(msg)
        except Exception as exc:
            client = getattr(ws, "client", ws)
            logging.warning("WebSocket send failed for %s: %s", client, exc)
            close = getattr(ws, "close", None)
            if close:
                with suppress(Exception):
                    res = close()
                    if inspect.isawaitable(res):
                        await res
            dead.append(ws)

    for ws in dead:
        _clients.discard(ws)
        logging.info("WebSocket pruned: %s", getattr(ws, "client", ws))


@router.websocket("/ws")
async def ws(ws: WebSocket) -> None:
    """WebSocket endpoint broadcasting structured events."""
    await ws.accept()
    _clients.add(ws)
    logging.info("WebSocket connected: %s", ws.client)
    # hydrate late joiners with recent history
    for evt in _history[-40:]:
        await ws.send_text(json.dumps(evt, default=str))
    try:
        while True:
            # keepalive (we ignore any received data)
            await ws.receive_text()
    except (WebSocketDisconnect, asyncio.CancelledError):
        logging.info("WebSocket disconnected: %s", ws.client)
    except Exception:
        logging.exception("Unexpected WebSocket error")
        with suppress(Exception):
            await ws.close()
    finally:
        _clients.discard(ws)


_heartbeat_task: asyncio.Task | None = None


async def _heartbeat_loop() -> None:
    while True:
        await broadcast({"type": "heartbeat", "now": utcnow()})
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
