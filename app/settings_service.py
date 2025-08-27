from __future__ import annotations
import json
from typing import Any, Dict
from .db import connect
from . import config

# Default settings derived from config.py constants
DEFAULTS: Dict[str, Any] = {
    "STATION_ID": config.STATION_ID,
    "REGION_ID": config.REGION_ID,
    "DATASOURCE": config.DATASOURCE,
    "VENUE": config.VENUE,
    "SALES_TAX": config.SALES_TAX,
    "BROKER_BUY": config.BROKER_BUY,
    "BROKER_SELL": config.BROKER_SELL,
    "RELIST_HAIRCUT": config.RELIST_HAIRCUT,
    "MOM_THRESHOLD": config.MOM_THRESHOLD,
    "MIN_DAYS_TRADED": config.MIN_DAYS_TRADED,
    "MIN_DAILY_VOL": config.MIN_DAILY_VOL,
    "SPREAD_BUFFER": config.SPREAD_BUFFER,
}


def _coerce(key: str, value: str) -> Any:
    """Coerce string values back to the type of the default."""
    default = DEFAULTS.get(key)
    if isinstance(default, bool):
        return value.lower() in {"1", "true", "yes"}
    if isinstance(default, int) and not isinstance(default, bool):
        return int(value)
    if isinstance(default, float):
        return float(value)
    return value


def get_settings() -> Dict[str, Any]:
    """Return current settings merged with defaults."""
    con = connect()
    try:
        rows = con.execute("SELECT key, value FROM app_settings").fetchall()
    finally:
        con.close()
    stored = {k: _coerce(k, v) for k, v in rows}
    merged: Dict[str, Any] = {}
    for key, default in DEFAULTS.items():
        merged[key] = stored.get(key, default)
    return merged


def update_settings(updates: Dict[str, Any]) -> None:
    """Persist settings into the database."""
    con = connect()
    try:
        for key, value in updates.items():
            if key not in DEFAULTS:
                continue
            con.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)),
            )
        con.commit()
    finally:
        con.close()
