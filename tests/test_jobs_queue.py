from pathlib import Path
import sys

# Ensure 'app' package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import jobs, esi


def test_job_queue_and_rate_limiter(monkeypatch):
    calls = []
    jobs.clear_queue()

    jobs.enqueue("a", lambda: calls.append("a"), priority="P2")
    jobs.enqueue("b", lambda: calls.append("b"), priority="P0")
    jobs.enqueue("c", lambda: calls.append("c"), priority="P1")

    monkeypatch.setattr(esi, "ERROR_LIMIT_REMAIN", 100)
    monkeypatch.setattr(esi, "ERROR_LIMIT_RESET", 1)
    limiter = jobs.RateLimiter()
    assert limiter.allow() is True

    jobs.run_next_job()
    jobs.run_next_job()
    jobs.run_next_job()
    assert calls == ["b", "c", "a"]

    monkeypatch.setattr(esi, "ERROR_LIMIT_REMAIN", 0)
    monkeypatch.setattr(esi, "ERROR_LIMIT_RESET", 20)
    assert limiter.allow() is False
    assert jobs.RateLimiter().backoff() >= 20


def test_worker_continues_after_job_error(monkeypatch):
    calls = []
    jobs.clear_queue()

    def bad():
        raise RuntimeError("boom")

    def good():
        calls.append("ok")

    jobs.enqueue("bad", bad)
    jobs.enqueue("good", good)

    monkeypatch.setattr(esi, "ERROR_LIMIT_REMAIN", 100)
    limiter = jobs.RateLimiter()

    sleep_calls = {"n": 0}

    def fake_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] > 5:
            raise SystemExit()

    monkeypatch.setattr(jobs.time, "sleep", fake_sleep)

    try:
        jobs.worker(limiter)
    except SystemExit:
        pass

    assert calls == ["ok"]

