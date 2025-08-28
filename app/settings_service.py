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
    "DEAL_THRESHOLDS": {"great_pct": 0.08, "good_pct": 0.04, "neutral_pct": 0.01},
    "CONFIDENCE_WEIGHTS": {"vol": 0.4, "freshness": 0.3, "stability": 0.3},
    "SHOW_ALL_DEFAULT": False,
}

# Metadata used for validation and UI hints
FIELD_META: Dict[str, Dict[str, Any]] = {
    "STATION_ID": {"type": int, "min": 1},
    "REGION_ID": {"type": int, "min": 1},
    "DATASOURCE": {"type": str},
    "VENUE": {"type": str},
    "SALES_TAX": {"type": float, "min": 0.0, "max": 1.0},
    "BROKER_BUY": {"type": float, "min": 0.0, "max": 1.0},
    "BROKER_SELL": {"type": float, "min": 0.0, "max": 1.0},
    "RELIST_HAIRCUT": {"type": float, "min": 0.0, "max": 1.0},
    "MOM_THRESHOLD": {"type": float, "min": 0.0, "max": 1.0},
    "MIN_DAYS_TRADED": {"type": int, "min": 0},
    "MIN_DAILY_VOL": {"type": int, "min": 0},
    "SPREAD_BUFFER": {"type": float, "min": 0.0, "max": 1.0},
    "DEAL_THRESHOLDS": {"type": dict},
    "CONFIDENCE_WEIGHTS": {"type": dict},
    "SHOW_ALL_DEFAULT": {"type": bool},
}


def validate_settings(updates: Dict[str, Any]) -> None:
    """Validate incoming settings against type and range constraints."""
    for key, value in updates.items():
        meta = FIELD_META.get(key)
        if not meta:
            raise ValueError(f"Unknown setting {key}")
        expected = meta.get("type")
        if expected is int:
            if isinstance(value, float) and not value.is_integer():
                raise ValueError(f"{key} must be an integer")
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be an integer")
        elif expected is float:
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be a number")
        elif expected is str:
            value = str(value)
        if "min" in meta and value < meta["min"]:
            raise ValueError(f"{key} must be >= {meta['min']}")
        if "max" in meta and value > meta["max"]:
            raise ValueError(f"{key} must be <= {meta['max']}")
        # Persist coerced value back into the dict for downstream use
        updates[key] = value


def _coerce(key: str, value: str) -> Any:
    """Coerce string values back to the type of the default."""
    default = DEFAULTS.get(key)
    if isinstance(default, bool):
        return value.lower() in {"1", "true", "yes"}
    if isinstance(default, int) and not isinstance(default, bool):
        return int(value)
    if isinstance(default, float):
        return float(value)
    if isinstance(default, (dict, list)):
        return json.loads(value)
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
