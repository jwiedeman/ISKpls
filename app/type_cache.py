from __future__ import annotations
from typing import Dict, Optional

from .db import connect

_type_name_cache: Dict[int, str] | None = None


def refresh_type_name_cache() -> None:
    """Reload the type ID to name mapping from the database."""
    global _type_name_cache
    con = connect()
    try:
        _type_name_cache = dict(
            con.execute("SELECT type_id, name FROM types").fetchall()
        )
    finally:
        con.close()


def get_type_name(type_id: int) -> Optional[str]:
    """Return the cached type name for ``type_id`` if available."""
    if _type_name_cache is None:
        refresh_type_name_cache()
    return _type_name_cache.get(type_id) if _type_name_cache else None
