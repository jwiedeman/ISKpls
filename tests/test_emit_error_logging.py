import logging
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app import emit


def test_emit_sync_logs_broadcast_errors(monkeypatch, caplog):
    def boom(evt):
        raise RuntimeError("boom")

    monkeypatch.setattr(emit, "broadcast", boom)

    with caplog.at_level(logging.ERROR):
        emit.emit_sync({"type": "x"})

    assert any("broadcast failed" in r.message for r in caplog.records)
