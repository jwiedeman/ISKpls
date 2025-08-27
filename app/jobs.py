from __future__ import annotations
from datetime import datetime
import json
from typing import Any, Optional
from . import db


def record_job(name: str, ok: bool, details: Optional[Any] = None) -> None:
    """Record a job execution in the jobs_history table."""
    con = db.connect()
    try:
        con.execute(
            """
            INSERT INTO jobs_history(name, ts_utc, ok, details_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                datetime.utcnow().isoformat(),
                1 if ok else 0,
                json.dumps(details) if details is not None else None,
            ),
        )
        con.commit()
    finally:
        con.close()
