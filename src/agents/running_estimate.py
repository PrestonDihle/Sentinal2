"""
SENTINEL2 — Running Estimate Engine
Maintains the permanently growing longitudinal intelligence picture.
Uses Gemini Flash for synthesis/delta detection.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from src.db.connection import execute_query, get_cursor
from src.utils.llm import call_llm, call_llm_json
from src.agents.context_loader import load_task_prompt

logger = logging.getLogger("sentinel2.running_estimate")


def run_running_estimate(run_date: Optional[str] = None) -> dict:
    """
    Generate today's running estimate by comparing today's processed
    collection against the prior day's estimate.

    Uses Gemini Flash (component="running_estimate").

    Returns the parsed running estimate dict.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"Generating running estimate for {run_date}")

    # Fetch today's processed collection
    today_items = execute_query(
        """SELECT title, summary, significance, pir_id, sir_id,
                  confidence, country, group_tag, topic, source_url
           FROM processed_collection
           WHERE run_date = %s
           ORDER BY significance DESC""",
        (run_date,),
    )

    if not today_items:
        logger.warning(f"No processed collection for {run_date} — skipping estimate")
        return {"run_date": run_date, "status": "skipped", "reason": "no_collection"}

    # Fetch prior day's running estimate
    yesterday = (date.fromisoformat(run_date) - timedelta(days=1)).isoformat()
    prior_rows = execute_query(
        """SELECT event_summary, pir_mapping, trajectory, delta_notes,
                  state_of_play, cumulative_patterns
           FROM running_estimate
           WHERE run_date = %s""",
        (yesterday,),
    )
    prior_estimate = prior_rows[0] if prior_rows else None

    # Build prompt
    system_prompt = load_task_prompt("running_estimate.txt")
    user_prompt = _build_estimate_prompt(run_date, today_items, prior_estimate)

    # Call LLM
    result = call_llm_json(
        system_prompt=system_prompt,
        prompt=user_prompt,
        component="running_estimate",
    )

    if not result:
        logger.error("Running estimate LLM call returned empty result")
        return {"run_date": run_date, "status": "failed"}

    # Ensure run_date is set
    result["run_date"] = run_date

    # Store in database
    _store_estimate(result)

    # Check for trajectory changes
    if prior_estimate:
        _check_trajectory_changes(run_date, result, prior_estimate)

    logger.info(f"Running estimate complete for {run_date}")
    return result


def get_latest_estimate(before_date: Optional[str] = None) -> Optional[dict]:
    """Fetch the most recent running estimate."""
    if before_date:
        rows = execute_query(
            """SELECT * FROM running_estimate
               WHERE run_date < %s ORDER BY run_date DESC LIMIT 1""",
            (before_date,),
        )
    else:
        rows = execute_query(
            "SELECT * FROM running_estimate ORDER BY run_date DESC LIMIT 1"
        )
    return rows[0] if rows else None


# ── Internal Helpers ──────────────────────────────────────────────────

def _build_estimate_prompt(
    run_date: str,
    today_items: list[dict],
    prior_estimate: Optional[dict],
) -> str:
    """Build the user prompt for the running estimate LLM call."""
    parts = [f"Run Date: {run_date}\n"]

    # Today's collection
    parts.append("TODAY'S PROCESSED COLLECTION:")
    for item in today_items:
        parts.append(
            f"  [{item.get('significance', '?')}] {item.get('title', 'Untitled')}\n"
            f"    PIR: {item.get('pir_id', 'N/A')}, SIR: {item.get('sir_id', 'N/A')}\n"
            f"    Confidence: {item.get('confidence', 'N/A')}\n"
            f"    Country: {item.get('country', 'N/A')}, "
            f"Topic: {item.get('topic', 'N/A')}\n"
            f"    Summary: {item.get('summary', 'N/A')}"
        )

    # Prior estimate
    if prior_estimate:
        parts.append("\nPRIOR DAY'S RUNNING ESTIMATE:")
        parts.append(f"  Event Summary: {prior_estimate.get('event_summary', 'N/A')}")
        pir_map = prior_estimate.get("pir_mapping", "")
        if isinstance(pir_map, str):
            parts.append(f"  PIR Mapping: {pir_map}")
        else:
            parts.append(f"  PIR Mapping: {json.dumps(pir_map)}")
        traj = prior_estimate.get("trajectory", "")
        if isinstance(traj, str):
            parts.append(f"  Trajectory: {traj}")
        else:
            parts.append(f"  Trajectory: {json.dumps(traj)}")
        parts.append(f"  Delta Notes: {prior_estimate.get('delta_notes', 'N/A')}")
        cum = prior_estimate.get("cumulative_patterns", "")
        if isinstance(cum, str):
            parts.append(f"  Cumulative Patterns: {cum}")
        else:
            parts.append(f"  Cumulative Patterns: {json.dumps(cum)}")
    else:
        parts.append(
            "\nNo prior running estimate available — this is the first run. "
            "Establish initial baselines for all entities."
        )

    return "\n".join(parts)


def _store_estimate(result: dict):
    """Store running estimate in the database."""
    def _json_str(val):
        if isinstance(val, (dict, list)):
            return json.dumps(val)
        return str(val) if val else ""

    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO running_estimate
                   (run_date, event_summary, pir_mapping, trajectory,
                    delta_notes, state_of_play, cumulative_patterns)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   event_summary = VALUES(event_summary),
                   pir_mapping = VALUES(pir_mapping),
                   trajectory = VALUES(trajectory),
                   delta_notes = VALUES(delta_notes),
                   state_of_play = VALUES(state_of_play),
                   cumulative_patterns = VALUES(cumulative_patterns)""",
            (
                result.get("run_date"),
                result.get("event_summary", ""),
                _json_str(result.get("pir_mapping", {})),
                _json_str(result.get("trajectory", {})),
                result.get("delta_notes", ""),
                _json_str(result.get("state_of_play", {})),
                _json_str(result.get("cumulative_patterns", [])),
            ),
        )


def _check_trajectory_changes(
    run_date: str, current: dict, prior: dict
):
    """Detect and log trajectory changes between consecutive estimates."""
    current_traj = current.get("trajectory", {})
    prior_traj = prior.get("trajectory", {})

    if isinstance(current_traj, str):
        try:
            current_traj = json.loads(current_traj)
        except (json.JSONDecodeError, TypeError):
            current_traj = {}
    if isinstance(prior_traj, str):
        try:
            prior_traj = json.loads(prior_traj)
        except (json.JSONDecodeError, TypeError):
            prior_traj = {}

    for pir_key in ["PIR1", "PIR2", "PIR3", "PIR4"]:
        old_val = prior_traj.get(pir_key, "UNKNOWN")
        new_val = current_traj.get(pir_key, "UNKNOWN")
        if old_val != new_val:
            logger.info(
                f"Trajectory change: {pir_key} {old_val} → {new_val}"
            )
            with get_cursor() as cursor:
                cursor.execute(
                    """INSERT INTO trajectory_changes
                           (run_date, pir_id, old_trajectory, new_trajectory, reason)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (run_date, pir_key, old_val, new_val,
                     current.get("delta_notes", "")),
                )
