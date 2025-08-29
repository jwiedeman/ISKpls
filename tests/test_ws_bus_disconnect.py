import asyncio
import json
import logging
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app import ws_bus


class GoodWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, txt: str) -> None:
        self.sent.append(txt)


class BadWS:
    async def send_text(self, txt: str) -> None:
        raise RuntimeError("boom")


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
    assert any("WebSocket send failed" in r.message for r in caplog.records)
    ws_bus._clients.clear()
