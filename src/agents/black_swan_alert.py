"""
SENTINEL2 — Black Swan Alert System
Monitors Group 5 output for new or escalating Black Swan events.
Generates out-of-cycle alert reports using Claude Sonnet.
"""

import json
import logging
from datetime import date
from typing import Optional

from src.db.connection import execute_query, get_cursor
from src.utils.llm import call_llm
from src.agents.context_loader import build_analyst_context, format_context_block, load_task_prompt

logger = logging.getLogger("sentinel2.black_swan")


def check_and_alert(
    group5_output: dict,
    run_date: Optional[str] = None,
) -> dict:
    """
    Evaluate Group 5 output for Black Swan alert triggers.

    Alert triggers:
      1. new_event = true on any watchlist item
      2. new_supporting_evidence = true on an existing watchlist item

    Returns dict with alert_triggered flag and any generated reports.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    watchlist = group5_output.get("watchlist", [])
    if not watchlist:
        logger.info("No Black Swan watchlist items — no alert needed")
        return {"alert_triggered": False, "run_date": run_date}

    # Identify trigger events
    trigger_events = [
        item for item in watchlist
        if item.get("new_event") or item.get("new_supporting_evidence")
    ]

    if not trigger_events:
        logger.info(
            f"Black Swan watchlist has {len(watchlist)} items, "
            "but none triggered alert dispatch"
        )
        _store_watchlist(run_date, watchlist)
        return {"alert_triggered": False, "run_date": run_date, "watchlist_size": len(watchlist)}

    logger.info(
        f"BLACK SWAN ALERT TRIGGERED: {len(trigger_events)} events "
        f"({sum(1 for e in trigger_events if e.get('new_event'))} new, "
        f"{sum(1 for e in trigger_events if e.get('new_supporting_evidence'))} escalating)"
    )

    # Generate alert reports
    alerts = []
    for event in trigger_events:
        report = _generate_alert_report(event, group5_output, run_date)
        if report:
            alerts.append(report)
            _store_alert(run_date, event, report)

    _store_watchlist(run_date, watchlist)

    return {
        "alert_triggered": True,
        "run_date": run_date,
        "alerts_generated": len(alerts),
        "trigger_events": [e.get("event_name", "Unknown") for e in trigger_events],
        "alerts": alerts,
    }


def get_active_watchlist() -> list[dict]:
    """Fetch the most recent Black Swan watchlist."""
    rows = execute_query(
        """SELECT * FROM black_swan_alerts
           WHERE alert_type = 'watchlist'
           ORDER BY run_date DESC LIMIT 1"""
    )
    if rows and rows[0].get("watchlist_json"):
        try:
            return json.loads(rows[0]["watchlist_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    return []


# ── Internal Helpers ──────────────────────────────────────────────────

def _generate_alert_report(
    event: dict,
    group5_output: dict,
    run_date: str,
) -> Optional[str]:
    """Generate a full Black Swan Alert Report using Claude Sonnet."""
    system_prompt = load_task_prompt("black_swan_alert.txt")

    # Build context
    context = build_analyst_context(run_date)
    context_block = format_context_block(context)

    # Build user prompt
    user_parts = [
        f"BLACK SWAN EVENT: {event.get('event_name', 'Unspecified Event')}",
        f"Probability Band: {event.get('probability', 'Unknown')}",
        f"Impact Tier: {event.get('impact_tier', 'Unknown')}",
        f"Trigger: {'NEW EVENT' if event.get('new_event') else 'NEW SUPPORTING EVIDENCE'}",
        "",
        "KEY WEAK SIGNALS:",
        json.dumps(event.get("weak_signals", []), indent=2),
        "",
        "DISCONFIRMING EVIDENCE:",
        json.dumps(event.get("disconfirming_evidence", []), indent=2),
        "",
        "FULL GROUP 5 ANALYSIS:",
        json.dumps(group5_output.get("synthesis", {}), indent=2),
        "",
        "CONSENSUS CHALLENGE:",
        group5_output.get("consensus_challenge", "N/A"),
        "",
        context_block,
    ]

    user_prompt = "\n".join(user_parts)

    # Use Claude Sonnet for alert generation (high-quality reasoning)
    report = call_llm(
        system_prompt=system_prompt,
        prompt=user_prompt,
        component="analysis_group_5",  # Sonnet tier
    )

    if report:
        logger.info(
            f"Black Swan alert report generated for: "
            f"{event.get('event_name', 'Unknown')} ({len(report)} chars)"
        )
    return report


def _store_alert(run_date: str, event: dict, report: str):
    """Store a Black Swan alert in the database."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO black_swan_alerts
                   (run_date, alert_type, event_name, probability_band,
                    impact_tier, is_new_event, report_text, watchlist_json)
               VALUES (%s, 'alert', %s, %s, %s, %s, %s, %s)""",
            (
                run_date,
                event.get("event_name", "Unknown"),
                event.get("probability", ""),
                event.get("impact_tier", ""),
                event.get("new_event", False),
                report,
                json.dumps(event),
            ),
        )


def _store_watchlist(run_date: str, watchlist: list[dict]):
    """Store the daily Black Swan watchlist snapshot."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO black_swan_alerts
                   (run_date, alert_type, event_name, watchlist_json)
               VALUES (%s, 'watchlist', 'Daily Watchlist', %s)
               ON DUPLICATE KEY UPDATE
                   watchlist_json = VALUES(watchlist_json)""",
            (run_date, json.dumps(watchlist)),
        )
