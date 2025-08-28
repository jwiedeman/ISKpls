from __future__ import annotations
from typing import Dict, Optional, Iterable, Any

import requests

from .db import connect
from .esi import BASE
from .config import DATASOURCE

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

def _fetch_details_from_esi(ids: list[int]) -> Dict[int, Dict[str, Any]]:
    """Fetch type details from ESI for the given IDs."""
    result: Dict[int, Dict[str, Any]] = {}
    group_cache: Dict[int, int] = {}
    for tid in ids:
        resp = requests.get(
            f"{BASE}/universe/types/{tid}/",
            params={"datasource": DATASOURCE},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        group_id = data.get("group_id")
        category_id = None
        if group_id:
            if group_id not in group_cache:
                g_resp = requests.get(
                    f"{BASE}/universe/groups/{group_id}/",
                    params={"datasource": DATASOURCE},
                    timeout=30,
                )
                g_resp.raise_for_status()
                group_cache[group_id] = g_resp.json().get("category_id")
            category_id = group_cache.get(group_id)
        meta_level = None
        for attr in data.get("dogma_attributes", []):
            if attr.get("attribute_id") == 633:
                meta_level = attr.get("value")
                break
        result[tid] = {
            "name": data.get("name"),
            "group_id": group_id,
            "category_id": category_id,
            "volume": data.get("volume"),
            "meta_level": meta_level,
            "market_group_id": data.get("market_group_id"),
        }
    return result


def ensure_type_names(ids: Iterable[int]) -> Dict[int, str]:
    """Ensure the provided ``ids`` have names cached, fetching from ESI if needed."""
    unique_ids = list({int(i) for i in ids})
    if not unique_ids:
        return {}
    global _type_name_cache
    if _type_name_cache is None:
        refresh_type_name_cache()
    known: Dict[int, str] = {}
    missing: list[int] = []
    for tid in unique_ids:
        if _type_name_cache and tid in _type_name_cache:
            known[tid] = _type_name_cache[tid]
        else:
            missing.append(tid)
    if missing:
        con = connect()
        try:
            placeholders = ",".join("?" for _ in missing)
            rows = con.execute(
                f"SELECT type_id, name FROM types WHERE type_id IN ({placeholders})",
                missing,
            ).fetchall()
            for tid, name in rows:
                known[tid] = name
                if _type_name_cache is not None:
                    _type_name_cache[tid] = name
            still_missing = [tid for tid in missing if tid not in known]
            if still_missing:
                fetched = _fetch_details_from_esi(still_missing)
                if fetched:
                    con.executemany(
                        """
                        INSERT OR REPLACE INTO types(
                            type_id, name, group_id, category_id, volume, meta_level, market_group_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                tid,
                                info.get("name"),
                                info.get("group_id"),
                                info.get("category_id"),
                                info.get("volume"),
                                info.get("meta_level"),
                                info.get("market_group_id"),
                            )
                            for tid, info in fetched.items()
                        ],
                    )
                    con.commit()
                    for tid, info in fetched.items():
                        name = info.get("name")
                        if name:
                            known[tid] = name
                            if _type_name_cache is not None:
                                _type_name_cache[tid] = name
        finally:
            con.close()
    return known


def get_type_name(type_id: int) -> Optional[str]:
    """Return the cached type name for ``type_id``, fetching if unknown."""
    if _type_name_cache is None or type_id not in _type_name_cache:
        ensure_type_names([type_id])
    return _type_name_cache.get(type_id) if _type_name_cache else None
