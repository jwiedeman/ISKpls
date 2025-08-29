from datetime import datetime, timezone

from app.util import utcnow, utcnow_dt, parse_utc


def test_utcnow_format():
    ts = utcnow()
    # ensure no exception on parsing
    parsed = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    assert parsed.tzinfo is None


def test_utcnow_dt_timezone():
    dt = utcnow_dt()
    assert dt.tzinfo is timezone.utc


def test_parse_utc_naive_to_aware():
    dt = parse_utc("2023-01-01 00:00:00")
    assert dt.tzinfo is timezone.utc
    assert dt.isoformat() == "2023-01-01T00:00:00+00:00"
