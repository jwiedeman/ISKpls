import json
import time
from .db import connect
from .market import evaluate_type
from .config import (
    MIN_DAILY_VOL,
    STATION_ID,
    REC_FRESH_MS,
    MOM_THRESHOLD,
)
from .jobs import record_job
from .emit import build_started, build_progress, build_finished


def build_recommendations(
    limit: int = 50, verbose: bool = False, dry_run: bool = False
):
    """Populate the recommendations table with top candidates.

    When ``dry_run`` is ``True`` the database is left untouched and a summary
    of pipeline counts is returned instead of inserted rows.

    Emits ``build_*`` events so the UI can surface progress for the
    recommendations build. When ``verbose`` is ``True`` extra progress
    updates are sent to help manual QA.
    """

    t0 = time.time()
    con = connect()
    try:
        rows = con.execute(
            "SELECT type_id, mom_pct FROM type_trends WHERE vol_30d_avg >= ? ORDER BY mom_pct DESC LIMIT ?",
            (MIN_DAILY_VOL, limit),
        ).fetchall()

        candidates = len(rows)
        bid = build_started(
            "recommendations", {"fresh_ms": REC_FRESH_MS, "candidates": candidates}
        )
        build_progress(bid, 10, "collect", f"candidates={candidates}")

        # freshness gate ----------------------------------------------------
        threshold = f"-{REC_FRESH_MS // 1000} seconds"
        fresh_ids = {
            tid
            for (tid,) in con.execute(
                "SELECT DISTINCT type_id FROM market_snapshots WHERE ts_utc >= datetime('now', ?)",
                (threshold,),
            ).fetchall()
        }
        fresh_pass = sum(1 for tid, _ in rows if tid in fresh_ids)
        build_progress(
            bid,
            30,
            "freshness",
            f"pass={fresh_pass} fail={candidates - fresh_pass}",
        )

        # volume and MoM gates ---------------------------------------------
        vol_pass = candidates  # initial query already enforces volume
        build_progress(
            bid,
            45,
            "volume",
            f"min_daily_vol={MIN_DAILY_VOL} pass={vol_pass} drop=0",
        )
        mom_pass = sum(1 for _, m in rows if m is not None and m >= MOM_THRESHOLD)
        build_progress(
            bid,
            60,
            "mom",
            f"min_mom={MOM_THRESHOLD} pass={mom_pass} drop={candidates - mom_pass}",
        )

        results = []
        for i, (type_id, _) in enumerate(rows, start=1):
            rec = evaluate_type(type_id)
            if not rec:
                continue
            results.append(rec)
            if not dry_run:
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
            if verbose and mom_pass:
                pct = 60 + int(i / mom_pass * 30)
                build_progress(bid, pct, "score", f"scored={i}")

        scored = len(results)
        build_progress(bid, 90, "score", f"scored={scored}")
        ms = int((time.time() - t0) * 1000)

        if dry_run:
            build_finished(bid, True, rows=scored, ms=ms)
            return {
                "candidates": candidates,
                "fresh_pass": fresh_pass,
                "vol_pass": vol_pass,
                "mom_pass": mom_pass,
                "scored": scored,
                "would_write": scored,
            }

        build_progress(bid, 100, "upsert", f"{scored} rows")
        con.commit()
        record_job("recommendations", True, {"count": scored})
        build_finished(bid, True, rows=scored, ms=ms)
        return results
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        if not dry_run:
            record_job("recommendations", False, {"error": str(e)})
        build_finished(bid, False, rows=0, ms=ms, error=str(e))
        raise
    finally:
        con.close()
