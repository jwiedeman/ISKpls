import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import esi
from app.status import STATUS

class DummyResp:
    status_code = 200
    headers = {
        "X-ESI-Error-Limit-Remain": "80",
        "X-ESI-Error-Limit-Reset": "12",
    }
    def json(self):
        return {}


def test_esi_updates_status(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=30):
        return DummyResp()
    monkeypatch.setattr(esi.requests, "get", fake_get)
    STATUS["esi"] = {"remain": 0, "reset": 0}
    esi.get("http://example.com")
    assert STATUS["esi"]["remain"] == 80
    assert STATUS["esi"]["reset"] == 12
