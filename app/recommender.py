from datetime import datetime
import json
from .db import connect
from .market import evaluate_type
from .config import MIN_DAILY_VOL
from .jobs import record_job


def build_recommendations(limit=50):
    """Populate the recommendations table with top candidates."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT type_id FROM type_trends WHERE vol_30d_avg >= ? ORDER BY mom_pct DESC LIMIT ?",
            (MIN_DAILY_VOL, limit),
        ).fetchall()
        now = datetime.utcnow().isoformat()
        results = []
        for (type_id,) in rows:
            rec = evaluate_type(type_id)
            if not rec:
                continue
            con.execute(
                """
                INSERT OR REPLACE INTO recommendations
                (type_id, ts_utc, net_pct, uplift_mom, daily_capacity, rationale_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["type_id"],
                    now,
                    rec["net_spread_pct"],
                    rec["uplift_mom"],
                    rec["daily_isk_capacity"],
                    json.dumps(rec),
                ),
            )
            results.append(rec)
        con.commit()
        record_job("recommendations", True, {"count": len(results)})
        return results
    except Exception as e:
        record_job("recommendations", False, {"error": str(e)})
        raise
    finally:
        con.close()
