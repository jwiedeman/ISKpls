import asyncio
import json
from datetime import datetime, timezone
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app import ws_bus


class GoodWS:
    def __init__(self):
        self.sent = []
        self.client = "good"

    async def send_text(self, txt: str) -> None:
        self.sent.append(txt)


def test_broadcast_serializes_datetimes():
    good = GoodWS()
    ws_bus._clients.clear()
    ws_bus._clients.add(good)
    ws_bus._history.clear()

    evt = {"type": "test", "when": datetime(2024, 1, 1, tzinfo=timezone.utc)}
    asyncio.run(ws_bus.broadcast(evt))

    assert json.loads(good.sent[0])["when"] == str(evt["when"])
    ws_bus._clients.clear()
    ws_bus._history.clear()
