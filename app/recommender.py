import json
import time
from .db import connect
from .market import evaluate_type
from .config import MIN_DAILY_VOL, STATION_ID
from .jobs import record_job
from .emit import build_started, build_progress, build_finished


def build_recommendations(limit: int = 50, verbose: bool = False):
    """Populate the recommendations table with top candidates.

    Emits ``build_*`` events so the UI can surface progress for the
    recommendations build. When ``verbose`` is ``True`` extra progress
    updates are sent to help manual QA.
    """

    t0 = time.time()
    con = connect()
    try:
        rows = con.execute(
            "SELECT type_id FROM type_trends WHERE vol_30d_avg >= ? ORDER BY mom_pct DESC LIMIT ?",
            (MIN_DAILY_VOL, limit),
        ).fetchall()

        bid = build_started("recommendations", {"candidates": len(rows)})
        build_progress(bid, 25, "filter", f"candidates {len(rows)}")

        results = []
        for i, (type_id,) in enumerate(rows, start=1):
            rec = evaluate_type(type_id)
            if not rec:
                continue
            con.execute(
                """
                INSERT INTO recommendations
                (type_id, station_id, ts_utc, net_pct, uplift_mom, daily_capacity, rationale_json)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
                ON CONFLICT(type_id, station_id) DO UPDATE SET
                    ts_utc = CURRENT_TIMESTAMP,
                    net_pct = excluded.net_pct,
                    uplift_mom = excluded.uplift_mom,
                    daily_capacity = excluded.daily_capacity,
                    rationale_json = excluded.rationale_json
                """,
                (
                    rec["type_id"],
                    STATION_ID,
                    rec["net_spread_pct"],
                    rec["uplift_mom"],
                    rec["daily_isk_capacity"],
                    json.dumps(rec),
                ),
            )
            results.append(rec)
            if verbose and len(rows):
                pct = 25 + int(i / len(rows) * 50)
                build_progress(bid, pct, "score", f"{i}/{len(rows)}")

        build_progress(bid, 75, "score", f"{len(results)} scored")
        build_progress(bid, 90, "upsert", f"{len(results)} ready")
        con.commit()
        build_progress(bid, 100, "upsert", f"{len(results)} rows")
        ms = int((time.time() - t0) * 1000)
        record_job("recommendations", True, {"count": len(results)})
        build_finished(bid, True, rows=len(results), ms=ms)
        return results
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        record_job("recommendations", False, {"error": str(e)})
        build_finished(bid, False, rows=0, ms=ms, error=str(e))
        raise
    finally:
        con.close()
