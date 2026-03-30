"""
SENTINEL2 — Weekly and Monthly Summarization Engine
Uses Gemini Flash for roll-up synthesis.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from src.db.connection import execute_query, get_cursor
from src.utils.llm import call_llm
from src.agents.context_loader import load_task_prompt

logger = logging.getLogger("sentinel2.summarizer")


def run_weekly_summary(run_date: Optional[str] = None) -> dict:
    """
    Generate weekly summary from 7 daily running estimate records.
    Runs on Sundays (or on demand).

    Returns dict with week metadata and summary text.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    rd = date.fromisoformat(run_date)
    # Week ends on run_date, starts 6 days prior
    week_start = (rd - timedelta(days=6)).isoformat()
    week_end = run_date

    logger.info(f"Generating weekly summary: {week_start} to {week_end}")

    # Fetch 7 days of running estimates
    estimates = execute_query(
        """SELECT run_date, event_summary, pir_mapping, trajectory,
                  delta_notes, cumulative_patterns
           FROM running_estimate
           WHERE run_date >= %s AND run_date <= %s
           ORDER BY run_date""",
        (week_start, week_end),
    )

    if not estimates:
        logger.warning("No running estimates found for weekly summary")
        return {"status": "skipped", "reason": "no_estimates"}

    # Build prompt
    system_prompt = load_task_prompt("summarizer_weekly.txt")
    system_prompt = system_prompt.replace("[MON DATE]", week_start)
    system_prompt = system_prompt.replace("[SUN DATE]", week_end)

    user_prompt = _format_estimates_for_summary(estimates)

    # Call Gemini Flash
    summary_text = call_llm(
        system_prompt=system_prompt,
        prompt=user_prompt,
        component="running_estimate",  # Flash tier
    )

    if not summary_text:
        logger.error("Weekly summary LLM call returned empty")
        return {"status": "failed"}

    # Determine week number (weeks since pipeline start or ISO week)
    week_number = rd.isocalendar()[1]

    # Store
    _store_weekly(week_start, week_end, week_number, summary_text)

    logger.info(f"Weekly summary complete: week {week_number}")
    return {
        "week_start": week_start,
        "week_end": week_end,
        "week_number": week_number,
        "summary_length": len(summary_text),
    }


def run_monthly_summary(run_date: Optional[str] = None) -> dict:
    """
    Generate monthly summary from all daily estimates and weekly
    summaries for the month. Runs on the 1st (for prior month) or on demand.

    Returns dict with month metadata and summary text.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    rd = date.fromisoformat(run_date)

    # Summarize the prior month
    if rd.day == 1:
        # Run on 1st → summarize previous month
        last_day_prev = rd - timedelta(days=1)
        month_start = last_day_prev.replace(day=1).isoformat()
        month_end = last_day_prev.isoformat()
        month_label = last_day_prev.strftime("%B %Y")
    else:
        # On-demand → summarize current month up to run_date
        month_start = rd.replace(day=1).isoformat()
        month_end = run_date
        month_label = rd.strftime("%B %Y")

    logger.info(f"Generating monthly summary: {month_label}")

    # Fetch daily estimates for the month
    estimates = execute_query(
        """SELECT run_date, event_summary, pir_mapping, trajectory,
                  delta_notes, cumulative_patterns
           FROM running_estimate
           WHERE run_date >= %s AND run_date <= %s
           ORDER BY run_date""",
        (month_start, month_end),
    )

    # Fetch weekly summaries overlapping the month
    weeklies = execute_query(
        """SELECT week_start, week_end, week_number, summary_text
           FROM weekly_summaries
           WHERE week_end >= %s AND week_start <= %s
           ORDER BY week_start""",
        (month_start, month_end),
    )

    if not estimates and not weeklies:
        logger.warning("No data found for monthly summary")
        return {"status": "skipped", "reason": "no_data"}

    # Build prompt
    system_prompt = load_task_prompt("summarizer_monthly.txt")
    system_prompt = system_prompt.replace("[MONTH]", month_label)
    system_prompt = system_prompt.replace("[N]", str(len(weeklies)))

    user_parts = []
    if weeklies:
        user_parts.append("WEEKLY SUMMARIES:")
        for w in weeklies:
            user_parts.append(
                f"\n--- Week {w.get('week_number', '?')}: "
                f"{w.get('week_start', '?')} to {w.get('week_end', '?')} ---\n"
                f"{w.get('summary_text', 'N/A')}"
            )

    if estimates:
        user_parts.append("\nDAILY RUNNING ESTIMATE HIGHLIGHTS:")
        for e in estimates:
            user_parts.append(
                f"  {e.get('run_date')}: {e.get('event_summary', 'N/A')[:200]}"
            )

    user_prompt = "\n".join(user_parts)

    summary_text = call_llm(
        system_prompt=system_prompt,
        prompt=user_prompt,
        component="running_estimate",  # Flash tier
    )

    if not summary_text:
        logger.error("Monthly summary LLM call returned empty")
        return {"status": "failed"}

    # Determine month number (1-12)
    month_number = date.fromisoformat(month_start).month

    _store_monthly(month_start, month_end, month_label, month_number, summary_text)

    logger.info(f"Monthly summary complete: {month_label}")
    return {
        "month": month_label,
        "month_number": month_number,
        "summary_length": len(summary_text),
    }


# ── Internal Helpers ──────────────────────────────────────────────────

def _format_estimates_for_summary(estimates: list[dict]) -> str:
    """Format running estimate records into a prompt block."""
    parts = []
    for e in estimates:
        traj = e.get("trajectory", "")
        if isinstance(traj, (dict, list)):
            traj = json.dumps(traj)

        parts.append(
            f"--- {e.get('run_date', '?')} ---\n"
            f"Event Summary: {e.get('event_summary', 'N/A')}\n"
            f"Trajectory: {traj}\n"
            f"Delta Notes: {e.get('delta_notes', 'N/A')}\n"
            f"Cumulative Patterns: {e.get('cumulative_patterns', 'N/A')}"
        )
    return "\n\n".join(parts)


def _store_weekly(
    week_start: str, week_end: str, week_number: int, summary_text: str
):
    """Store weekly summary in the database."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO weekly_summaries
                   (week_start, week_end, week_number, summary_text)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   summary_text = VALUES(summary_text)""",
            (week_start, week_end, week_number, summary_text),
        )


def _store_monthly(
    month_start: str, month_end: str, month_label: str,
    month_number: int, summary_text: str
):
    """Store monthly summary in the database."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO monthly_summaries
                   (month, month_start, month_end, month_number, summary_text)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   summary_text = VALUES(summary_text)""",
            (month_label, month_start, month_end, month_number, summary_text),
        )
