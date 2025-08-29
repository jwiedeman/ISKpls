from datetime import datetime, timezone


def utcnow() -> str:
    """Return current UTC time formatted for SQLite (``YYYY-MM-DD HH:MM:SS``)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def utcnow_dt() -> datetime:
    """Return the current timezone-aware UTC ``datetime``."""
    return datetime.now(timezone.utc)


def parse_utc(ts: str) -> datetime:
    """Parse a timestamp into a UTC-aware ``datetime``."""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
