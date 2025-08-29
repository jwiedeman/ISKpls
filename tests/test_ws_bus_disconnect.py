import asyncio
import json
import logging
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app import ws_bus
from starlette.websockets import WebSocketDisconnect


class GoodWS:
    def __init__(self):
        self.sent = []
        self.client = "good"

    async def send_text(self, txt: str) -> None:
        self.sent.append(txt)


class BadWS:
    def __init__(self):
        self.client = "bad"

    async def send_text(self, txt: str) -> None:
        raise RuntimeError("boom")


class OddWS:
    """WebSocket stub whose ``close`` returns a coroutine."""

    def __init__(self) -> None:
        self.client = "odd"
        self.closed = False

    async def send_text(self, txt: str) -> None:
        raise RuntimeError("boom")

    async def _aclose(self) -> None:
        self.closed = True

    def close(self):  # intentionally sync returning coroutine
        return self._aclose()


def test_broadcast_prunes_dead_clients(caplog):
    caplog.set_level(logging.INFO)
    good = GoodWS()
    bad = BadWS()
    ws_bus._clients.clear()
    ws_bus._clients.update({good, bad})
    asyncio.run(ws_bus.broadcast({"type": "test"}))
    assert good in ws_bus._clients
    assert bad not in ws_bus._clients
    assert good.sent[0] == json.dumps({"type": "test"})
    assert any("WebSocket send failed for bad" in r.message for r in caplog.records)
    assert any("WebSocket pruned" in r.message for r in caplog.records)
    ws_bus._clients.clear()


def test_broadcast_awaits_close_returning_coroutine():
    odd = OddWS()
    ws_bus._clients.clear()
    ws_bus._clients.add(odd)
    asyncio.run(ws_bus.broadcast({"type": "test"}))
    assert odd.closed
    assert odd not in ws_bus._clients
    ws_bus._clients.clear()


class DiscWS:
    def __init__(self) -> None:
        self.client = "disc"

    async def send_text(self, txt: str) -> None:
        raise WebSocketDisconnect(1000)


def test_broadcast_logs_disconnect(caplog):
    caplog.set_level(logging.INFO)
    disc = DiscWS()
    ws_bus._clients.clear()
    ws_bus._clients.add(disc)
    asyncio.run(ws_bus.broadcast({"type": "test"}))
    assert disc not in ws_bus._clients
    assert any("WebSocket disconnected during send: disc" in r.message for r in caplog.records)
    ws_bus._clients.clear()
