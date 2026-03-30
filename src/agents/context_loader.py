"""
SENTINEL2 — Context Loader
Assembles the bounded analyst context package for all 6 analysis groups.
Pure Python — no LLM calls.

Context package contents:
  1. Today's quantitative metrics dashboard (composite_scores + daily_values)
  2. Today's processed collection (processed_collection table)
  3. Last 7 days of running estimate records
  4. Last 3 completed weekly summaries
  5. Last 3 completed monthly summaries
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from src.db.connection import execute_query
from src.utils.config import get_pirs_dir

logger = logging.getLogger("sentinel2.context_loader")


def build_analyst_context(run_date: Optional[str] = None) -> dict:
    """
    Assemble bounded context package for analysis groups.

    Returns dict with keys: metrics, today, recent_daily, weekly, monthly.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"Building analyst context package for {run_date}")

    metrics_text = _build_metrics_dashboard(run_date)
    today_text = _build_today_collection(run_date)
    recent_daily_text = _build_running_estimates(run_date)
    weekly_text = _build_weekly_summaries()
    monthly_text = _build_monthly_summaries()

    context = {
        "metrics": metrics_text,
        "today": today_text,
        "recent_daily": recent_daily_text,
        "weekly": weekly_text,
        "monthly": monthly_text,
    }

    logger.info(f"Context package assembled for {run_date}")
    return context


def format_context_block(context: dict) -> str:
    """
    Format the context dict into the text block injected into
    analysis group system prompts (Block 3).
    """
    block = "CONTEXT PACKAGE — GROUND YOUR ANALYSIS IN THIS MATERIAL:\n\n"
    block += "[QUANTITATIVE METRICS DASHBOARD]\n"
    block += context["metrics"] + "\n\n"
    block += "[TODAY'S COLLECTION]\n"
    block += context["today"] + "\n\n"
    block += "[RUNNING ESTIMATE — LAST 7 DAYS]\n"
    block += context["recent_daily"] + "\n\n"
    block += "[WEEKLY SUMMARIES — LAST 3]\n"
    block += context["weekly"] + "\n\n"
    block += "[MONTHLY SUMMARIES — LAST 3]\n"
    block += context["monthly"] + "\n\n"
    block += (
        "Use the quantitative metrics dashboard to identify convergent signals across "
        "domains. When multiple metrics from unrelated domains simultaneously deviate "
        "from baseline, this significantly increases the probability of a real development. "
        "Ground your analysis in both the metrics and collection data. "
        "Do not recapitulate this context — analyze it.\n"
    )
    return block


def load_pir_text(pir_number: int) -> str:
    """Load full PIR text from the pirs/ directory."""
    pirs_dir = get_pirs_dir()
    pir_file = pirs_dir / f"PIR_{pir_number}.md"
    if pir_file.exists():
        return pir_file.read_text(encoding="utf-8")
    logger.warning(f"PIR file not found: {pir_file}")
    return f"(PIR {pir_number} text not available)"


def load_task_prompt(prompt_filename: str) -> str:
    """Load a task prompt text file from the prompts directory."""
    from src.utils.config import get_prompts_dir
    path = get_prompts_dir() / prompt_filename
    return path.read_text(encoding="utf-8").strip()


# ── Internal Builders ─────────────────────────────────────────────────

def _build_metrics_dashboard(run_date: str) -> str:
    """Build quantitative metrics dashboard text."""
    try:
        composite_rows = execute_query(
            "SELECT * FROM composite_scores WHERE run_date = %s",
            (run_date,),
        )
        value_rows = execute_query(
            """SELECT m.metric_id, m.name, m.domain, m.direction,
                      d.raw_value, d.z_score, d.anomaly_flag, d.trend_7d, d.notes
               FROM daily_values d
               JOIN metrics m ON d.metric_id = m.metric_id
               WHERE d.run_date = %s
               ORDER BY m.domain, m.metric_id""",
            (run_date,),
        )
    except Exception as e:
        logger.warning(f"Failed to load metrics dashboard: {e}")
        return "(Metrics dashboard unavailable — database may not be initialized.)"

    if not value_rows:
        return "(No quantitative metrics collected for today.)"

    lines = []

    # Composite score header
    if composite_rows:
        cs = composite_rows[0]
        alert = cs.get("alert_level", "UNKNOWN")
        anom_count = cs.get("anomalous_count", 0)
        total = cs.get("total_collected", 0)
        conv_note = cs.get("convergence_note", "")
        lines.append(
            f"COMPOSITE ANOMALY SCORE: {anom_count}/{total} metrics anomalous "
            f"— Alert Level: {alert}"
        )
        if conv_note:
            lines.append(f"CONVERGENCE: {conv_note}")
        lines.append("")

    # Group by domain
    current_domain = None
    for r in value_rows:
        domain = r.get("domain", "Unknown")
        if domain != current_domain:
            current_domain = domain
            lines.append(f"--- {domain} ---")

        value = r.get("raw_value")
        z = r.get("z_score")
        anomaly = r.get("anomaly_flag", 0)
        trend = r.get("trend_7d", "?")

        val_str = f"{value}" if value is not None else "N/A"
        z_str = f"z={z:+.2f}" if z is not None else "z=N/A"
        trend_arrows = {"UP": "^", "DOWN": "v", "FLAT": "=", "INSUFFICIENT": "?"}
        trend_sym = trend_arrows.get(trend, "?")
        flag = " ** ANOMALY **" if anomaly else ""

        lines.append(
            f"  [{r['metric_id']:02d}] {r['name']}: {val_str} "
            f"({z_str}, trend: {trend_sym}){flag}"
        )
        if r.get("notes") and anomaly:
            lines.append(f"       {r['notes']}")

    # Anomaly summary
    anomalous = [r for r in value_rows if r.get("anomaly_flag")]
    if anomalous:
        lines.append("")
        lines.append("ANOMALOUS METRICS REQUIRING ATTENTION:")
        for r in anomalous:
            lines.append(
                f"  - {r['name']} ({r['domain']}): value={r.get('raw_value')}, "
                f"z={r.get('z_score', '?')}, trend={r.get('trend_7d', '?')}"
            )

    return "\n".join(lines)


def _build_today_collection(run_date: str, max_items: int = 200) -> str:
    """
    Format today's processed collection items for analyst context.

    Prioritizes HIGH and MED significance items. LOW items are counted
    but not included in full to keep context within LLM token limits.
    Caps at max_items to stay under ~50K tokens for this block.
    """
    try:
        # Count totals by significance
        counts = execute_query(
            """SELECT significance, COUNT(*) as cnt
               FROM processed_collection WHERE run_date = %s
               GROUP BY significance""",
            (run_date,),
        )
        count_map = {r["significance"]: r["cnt"] for r in counts} if counts else {}
        total = sum(count_map.values())

        # Fetch HIGH items first, then MED, up to max_items
        high_items = execute_query(
            """SELECT title, summary, pir_id, sir_id, country, topic,
                      significance, confidence
               FROM processed_collection
               WHERE run_date = %s AND significance = 'HIGH'
               ORDER BY pir_id
               LIMIT %s""",
            (run_date, max_items),
        )

        remaining = max_items - len(high_items)
        med_items = []
        if remaining > 0:
            med_items = execute_query(
                """SELECT title, summary, pir_id, sir_id, country, topic,
                          significance, confidence
                   FROM processed_collection
                   WHERE run_date = %s AND significance = 'MED'
                   ORDER BY pir_id
                   LIMIT %s""",
                (run_date, remaining),
            )

    except Exception as e:
        logger.warning(f"Failed to load today's collection: {e}")
        return "(Collection data unavailable.)"

    if not high_items and not med_items:
        return "(No collection data available for today.)"

    lines = [
        f"TODAY'S COLLECTION SUMMARY: {total} items total "
        f"({count_map.get('HIGH', 0)} HIGH, {count_map.get('MED', 0)} MED, "
        f"{count_map.get('LOW', 0)} LOW)",
        ""
    ]

    for r in high_items + med_items:
        sig = r.get("significance", "?")
        summary = (r.get("summary") or "")[:300]  # Truncate long summaries
        lines.append(
            f"[{sig}] {r.get('title', 'Untitled')} "
            f"(PIR: {r.get('pir_id', '?')}, SIR: {r.get('sir_id', '?')}, "
            f"Confidence: {r.get('confidence', '?')})\n"
            f"  {summary}\n"
            f"  Country={r.get('country', '?')}, Topic={r.get('topic', '?')}"
        )

    shown = len(high_items) + len(med_items)
    if shown < total:
        lines.append(f"\n({total - shown} LOW-significance items omitted for brevity)")

    return "\n\n".join(lines)


def _build_running_estimates(run_date: str) -> str:
    """Format last 7 days of running estimate records."""
    start_date = (date.fromisoformat(run_date) - timedelta(days=7)).isoformat()
    try:
        records = execute_query(
            """SELECT * FROM running_estimate
               WHERE run_date >= %s AND run_date < %s
               ORDER BY run_date DESC""",
            (start_date, run_date),
        )
    except Exception as e:
        logger.warning(f"Failed to load running estimates: {e}")
        return "(Running estimate unavailable.)"

    if not records:
        return "(No running estimate records available yet — pipeline is in early operation.)"

    lines = []
    for r in records:
        lines.append(
            f"--- {r.get('run_date', 'Unknown Date')} ---\n"
            f"Event Summary: {r.get('event_summary', 'N/A')}\n"
            f"PIR Mapping: {r.get('pir_mapping', 'N/A')}\n"
            f"Trajectory: {r.get('trajectory', 'N/A')}\n"
            f"Delta Notes: {r.get('delta_notes', 'N/A')}\n"
            f"Cumulative Patterns: {r.get('cumulative_patterns', 'N/A')}"
        )
    return "\n\n".join(lines)


def _build_weekly_summaries() -> str:
    """Format last 3 weekly summaries."""
    try:
        records = execute_query(
            """SELECT * FROM weekly_summaries
               ORDER BY created_at DESC LIMIT 3"""
        )
    except Exception as e:
        logger.warning(f"Failed to load weekly summaries: {e}")
        return "(Weekly summaries unavailable.)"

    if not records:
        return "(No weekly summaries available yet — pipeline has not completed a full week.)"

    lines = []
    for r in records:
        lines.append(
            f"--- Week of {r.get('week_start', '?')} to {r.get('week_end', '?')} "
            f"(Week {r.get('week_number', '?')}) ---\n"
            f"{r.get('summary_text', 'N/A')}"
        )
    return "\n\n".join(lines)


def _build_monthly_summaries() -> str:
    """Format last 3 monthly summaries."""
    try:
        records = execute_query(
            """SELECT * FROM monthly_summaries
               ORDER BY created_at DESC LIMIT 3"""
        )
    except Exception as e:
        logger.warning(f"Failed to load monthly summaries: {e}")
        return "(Monthly summaries unavailable.)"

    if not records:
        return "(No monthly summaries available yet — pipeline has not completed a full month.)"

    lines = []
    for r in records:
        lines.append(
            f"--- {r.get('month', 'Unknown Month')} "
            f"(Month {r.get('month_number', '?')}) ---\n"
            f"{r.get('summary_text', 'N/A')}"
        )
    return "\n\n".join(lines)
