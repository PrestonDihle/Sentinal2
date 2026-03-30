"""
SENTINEL2 — Metrics Scoring Engine
Computes z-scores, anomaly detection, rolling statistics,
trend indicators, and composite alert levels.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

import numpy as np

from src.db.connection import get_cursor, execute_query
from src.utils.config import get_config

logger = logging.getLogger("sentinel2.metrics.scorer")


def score_daily_metrics(run_date: Optional[str] = None) -> dict:
    """
    Compute z-scores, anomaly flags, and composite alert for all metrics
    collected on the given date.

    Returns summary dict with alert_level and anomalous metrics.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    config = get_config()
    scoring_cfg = config.get("metrics", {}).get("scoring", {})
    z_threshold = scoring_cfg.get("z_score_threshold", 2.0)
    baseline_window = scoring_cfg.get("baseline_window_days", 90)

    # Fetch all metric definitions
    metrics = execute_query("SELECT * FROM metrics WHERE enabled = TRUE")
    if not metrics:
        logger.warning("No enabled metrics found")
        return {"alert_level": "NORMAL", "anomalous_count": 0}

    anomalous = []
    scored_count = 0

    for metric in metrics:
        metric_id = metric["metric_id"]
        direction = metric["direction"]
        threshold = float(metric.get("alert_threshold", z_threshold))

        # Fetch today's raw value
        today_rows = execute_query(
            "SELECT raw_value FROM daily_values WHERE metric_id = %s AND run_date = %s",
            (metric_id, run_date),
        )
        if not today_rows or today_rows[0]["raw_value"] is None:
            continue

        raw_value = float(today_rows[0]["raw_value"])

        # Fetch baseline data (last N days)
        baseline_start = (date.fromisoformat(run_date) - timedelta(days=baseline_window)).isoformat()
        baseline_rows = execute_query(
            """SELECT raw_value FROM daily_values
               WHERE metric_id = %s AND run_date >= %s AND run_date < %s
               AND raw_value IS NOT NULL AND data_quality = 'ok'
               ORDER BY run_date""",
            (metric_id, baseline_start, run_date),
        )

        baseline_values = [float(r["raw_value"]) for r in baseline_rows]

        if len(baseline_values) < 7:
            # Insufficient data for meaningful z-score
            _update_daily_value(metric_id, run_date, z_score=None, anomaly=False,
                                rolling_mean=None, rolling_std=None, trend="INSUFFICIENT")
            continue

        # Compute rolling stats
        arr = np.array(baseline_values)
        rolling_mean = float(np.mean(arr))
        rolling_std = float(np.std(arr))

        # Z-score
        if rolling_std > 0:
            z_score = (raw_value - rolling_mean) / rolling_std
        else:
            z_score = 0.0

        # Anomaly detection (direction-aware)
        is_anomaly = False
        if direction == "high" and z_score > threshold:
            is_anomaly = True
        elif direction == "low" and z_score < -threshold:
            is_anomaly = True
        elif direction == "both" and abs(z_score) > threshold:
            is_anomaly = True

        # 7-day trend
        trend = _compute_trend(baseline_values, raw_value)

        # Update daily_values record
        _update_daily_value(
            metric_id, run_date,
            z_score=round(z_score, 4),
            anomaly=is_anomaly,
            rolling_mean=round(rolling_mean, 6),
            rolling_std=round(rolling_std, 6),
            trend=trend,
        )
        scored_count += 1

        if is_anomaly:
            anomalous.append({
                "metric_id": metric_id,
                "name": metric["name"],
                "z_score": round(z_score, 2),
                "raw_value": raw_value,
                "rolling_mean": round(rolling_mean, 2),
                "direction": direction,
            })

    # Composite alert level
    n_anomalous = len(anomalous)
    if n_anomalous >= 9:
        alert_level = "CONVERGENT"
    elif n_anomalous >= 6:
        alert_level = "DEVELOPING"
    elif n_anomalous >= 3:
        alert_level = "HEIGHTENED"
    else:
        alert_level = "NORMAL"

    # Store composite score
    _store_composite(run_date, scored_count, n_anomalous, anomalous, alert_level)

    logger.info(
        f"Metrics scored: {scored_count} metrics, {n_anomalous} anomalous → {alert_level}"
    )

    return {
        "run_date": run_date,
        "scored_count": scored_count,
        "anomalous_count": n_anomalous,
        "alert_level": alert_level,
        "anomalous_metrics": anomalous,
    }


def _compute_trend(baseline: list[float], current: float) -> str:
    """Compute 7-day trend direction."""
    if len(baseline) < 7:
        return "INSUFFICIENT"

    last_7 = baseline[-7:]
    avg_7 = sum(last_7) / len(last_7)

    if len(baseline) >= 14:
        prev_7 = baseline[-14:-7]
        avg_prev = sum(prev_7) / len(prev_7)
    else:
        avg_prev = avg_7

    pct_change = (avg_7 - avg_prev) / abs(avg_prev) * 100 if avg_prev != 0 else 0

    if pct_change > 5:
        return "UP"
    elif pct_change < -5:
        return "DOWN"
    else:
        return "FLAT"


def _update_daily_value(
    metric_id: int,
    run_date: str,
    z_score: Optional[float],
    anomaly: bool,
    rolling_mean: Optional[float],
    rolling_std: Optional[float],
    trend: str,
):
    """Update z-score and anomaly fields in daily_values."""
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE daily_values
               SET z_score = %s, anomaly_flag = %s,
                   rolling_mean = %s, rolling_std = %s, trend_7d = %s
               WHERE metric_id = %s AND run_date = %s""",
            (z_score, anomaly, rolling_mean, rolling_std, trend, metric_id, run_date),
        )


def _store_composite(
    run_date: str,
    total: int,
    anomalous_count: int,
    anomalous: list[dict],
    alert_level: str,
):
    """Store composite score for the day."""
    convergence_note = ""
    if anomalous_count >= 3:
        domains = set(a.get("name", "").split()[0] for a in anomalous)
        convergence_note = f"Anomalies across: {', '.join(domains)}"

    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO composite_scores
                   (run_date, total_collected, anomalous_count,
                    anomalous_metrics, alert_level, convergence_note)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   total_collected = VALUES(total_collected),
                   anomalous_count = VALUES(anomalous_count),
                   anomalous_metrics = VALUES(anomalous_metrics),
                   alert_level = VALUES(alert_level),
                   convergence_note = VALUES(convergence_note)""",
            (run_date, total, anomalous_count,
             json.dumps(anomalous), alert_level, convergence_note),
        )


def collect_and_score_metric(
    metric_id: int,
    collection_fn_path: str,
    run_date: Optional[str] = None,
) -> dict:
    """
    Collect a single metric by calling its collection function,
    store the raw value, and return the result.

    Args:
        metric_id: ID from metrics table
        collection_fn_path: Dotted path like 'financial.collect_brent_wti_spread'
        run_date: ISO date string

    Returns:
        Result dict from collector function.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    # Dynamic import of collector function
    module_name, func_name = collection_fn_path.rsplit(".", 1)
    module = __import__(f"src.collectors.metrics.{module_name}", fromlist=[func_name])
    collect_fn = getattr(module, func_name)

    # Call collector
    result = collect_fn(run_date)
    value = result.get("value")
    raw_json = result.get("raw_json", {})
    notes = result.get("notes", "")

    # Determine data quality
    quality = "ok" if value is not None else "collection_failed"

    # Store in daily_values
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO daily_values
                   (metric_id, run_date, raw_value, raw_json, data_quality, notes)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   raw_value = VALUES(raw_value),
                   raw_json = VALUES(raw_json),
                   data_quality = VALUES(data_quality),
                   notes = VALUES(notes)""",
            (metric_id, run_date, value, json.dumps(raw_json), quality, notes),
        )

    logger.info(f"Metric {metric_id}: value={value}, quality={quality}")
    return result


def collect_all_metrics(run_date: Optional[str] = None) -> dict:
    """
    Collect all enabled metrics for the given date.
    Returns summary of collection results.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    metrics = execute_query("SELECT * FROM metrics WHERE enabled = TRUE ORDER BY metric_id")
    results = {"collected": 0, "failed": 0, "metrics": {}}

    for m in metrics:
        fn_path = m.get("collection_fn", "")
        if not fn_path:
            continue

        try:
            result = collect_and_score_metric(m["metric_id"], fn_path, run_date)
            if result.get("value") is not None:
                results["collected"] += 1
            else:
                results["failed"] += 1
            results["metrics"][m["name"]] = result.get("value")
        except Exception as e:
            logger.warning(f"Metric {m['name']} collection failed: {e}")
            results["failed"] += 1

    logger.info(f"Metrics collection: {results['collected']} ok, {results['failed']} failed")
    return results
