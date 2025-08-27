from __future__ import annotations
from typing import Dict, Any
from .db import connect

# Default scheduler configuration for known jobs
JOB_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "sync_character": {"enabled": True, "interval": 60},
    "refresh_trends": {"enabled": True, "interval": 1440},
    "snapshot_orders": {"enabled": True, "interval": 60},
    "refresh_type_valuations": {"enabled": True, "interval": 360},
    "recommender_scan": {"enabled": True, "interval": 60},
}

PREFIX = "SCHED_"


def get_scheduler_settings() -> Dict[str, Dict[str, Any]]:
    """Return current scheduler settings merged with defaults."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT key, value FROM app_settings WHERE key LIKE ?", (f"{PREFIX}%",)
        ).fetchall()
    finally:
        con.close()
    stored = {k: v for k, v in rows}
    result: Dict[str, Dict[str, Any]] = {}
    for name, meta in JOB_DEFAULTS.items():
        enabled_key = f"{PREFIX}{name}_ENABLED"
        interval_key = f"{PREFIX}{name}_INTERVAL"
        enabled_val = stored.get(enabled_key, "1" if meta["enabled"] else "0")
        interval_val = stored.get(interval_key, str(meta["interval"]))
        result[name] = {
            "enabled": enabled_val in {"1", "true", "True"},
            "interval": int(interval_val),
        }
    return result


def update_scheduler_settings(settings: Dict[str, Dict[str, Any]]) -> None:
    """Persist scheduler settings into app_settings."""
    con = connect()
    try:
        for name, cfg in settings.items():
            if name not in JOB_DEFAULTS:
                continue
            enabled_key = f"{PREFIX}{name}_ENABLED"
            interval_key = f"{PREFIX}{name}_INTERVAL"
            enabled = cfg.get("enabled", JOB_DEFAULTS[name]["enabled"])
            interval = cfg.get("interval", JOB_DEFAULTS[name]["interval"])
            con.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (enabled_key, "1" if enabled else "0"),
            )
            con.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (interval_key, str(int(interval))),
            )
        con.commit()
    finally:
        con.close()
