"""
SENTINEL2 — Report Generation Agent
Produces the daily intelligence brief and Black Swan alert reports.
Uses Gemini Flash for formatting/templating.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.db.connection import execute_query, get_cursor
from src.utils.llm import call_llm
from src.utils.config import get_project_root, get_reports_dir
from src.agents.context_loader import load_task_prompt

logger = logging.getLogger("sentinel2.reporter")

_TEMPLATES_DIR = get_project_root() / "templates"


def generate_daily_report(run_date: Optional[str] = None) -> dict:
    """
    Generate the daily intelligence brief HTML from analysis outputs.

    Steps:
      1. Gather all analysis group outputs, metrics, collection stats
      2. Call LLM (Gemini Flash) to produce report section content
      3. Render into HTML template
      4. Store in report_archive

    Returns dict with html content and metadata.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"Generating daily report for {run_date}")

    # Gather data
    report_data = _gather_report_data(run_date)

    # Generate report sections via LLM
    system_prompt = load_task_prompt("reporter.txt")
    user_prompt = _build_reporter_prompt(report_data)

    sections = call_llm(
        system_prompt=system_prompt,
        prompt=user_prompt,
        component="reporter",  # Gemini Flash
    )

    if not sections:
        logger.error("Reporter LLM returned empty output")
        return {"status": "failed", "run_date": run_date}

    # Parse LLM output into template variables
    template_vars = _parse_report_sections(sections, report_data)

    # Render HTML
    html = _render_template("report_template.html", template_vars)

    # Store
    _store_report_archive(run_date, report_data, html)

    # Save HTML file
    reports_dir = get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    html_path = reports_dir / f"sentinel2_daily_{run_date}.html"
    html_path.write_text(html, encoding="utf-8")

    logger.info(f"Daily report generated: {html_path} ({len(html)} chars)")
    return {
        "status": "ok",
        "run_date": run_date,
        "html_path": str(html_path),
        "html_length": len(html),
    }


def generate_black_swan_report(
    alert_data: dict,
    run_date: Optional[str] = None,
) -> dict:
    """
    Generate a Black Swan alert report HTML.

    Args:
        alert_data: Dict with alert sections from black_swan_alert.py
        run_date: ISO date string

    Returns dict with html content and path.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    from datetime import datetime
    template_vars = {
        "issued_at": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "alert_id": alert_data.get("alert_id", f"BSA-{run_date}"),
        "next_date": (date.fromisoformat(run_date) + timedelta(days=1)).isoformat(),
        **alert_data,
    }

    html = _render_template("black_swan_template.html", template_vars)

    reports_dir = get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    html_path = reports_dir / f"sentinel2_bsa_{run_date}_{template_vars['alert_id']}.html"
    html_path.write_text(html, encoding="utf-8")

    logger.info(f"Black Swan report generated: {html_path}")
    return {
        "status": "ok",
        "html_path": str(html_path),
        "html_length": len(html),
    }


# ── Data Gathering ────────────────────────────────────────────────────

def _gather_report_data(run_date: str) -> dict:
    """Gather all data needed for the daily report."""
    data = {"run_date": run_date}

    # Collection stats
    stats = execute_query(
        """SELECT significance, COUNT(*) as cnt
           FROM processed_collection WHERE run_date = %s
           GROUP BY significance""",
        (run_date,),
    )
    sig_counts = {s["significance"]: s["cnt"] for s in stats}
    data["total_items"] = sum(sig_counts.values())
    data["high_count"] = sig_counts.get("HIGH", 0)
    data["med_count"] = sig_counts.get("MEDIUM", 0)

    # SIR coverage
    sir_rows = execute_query(
        """SELECT DISTINCT sir_id FROM processed_collection
           WHERE run_date = %s AND sir_id IS NOT NULL""",
        (run_date,),
    )
    data["sir_count"] = len(sir_rows)

    # Cycle number
    archive_rows = execute_query("SELECT COUNT(*) as cnt FROM report_archive")
    data["cycle_number"] = (archive_rows[0]["cnt"] if archive_rows else 0) + 1

    # Next date
    data["next_date"] = (date.fromisoformat(run_date) + timedelta(days=1)).isoformat()

    # Analysis group outputs
    for gid in range(1, 7):
        rows = execute_query(
            """SELECT assessment_json, synthesis_text, trajectory, confidence_level
               FROM ae_assessments WHERE group_id = %s AND run_date = %s
               ORDER BY created_at DESC LIMIT 1""",
            (gid, run_date),
        )
        if rows:
            data[f"group_{gid}"] = rows[0]
        else:
            data[f"group_{gid}"] = {}

    # Composite score
    comp_rows = execute_query(
        "SELECT * FROM composite_scores WHERE run_date = %s", (run_date,)
    )
    data["composite"] = comp_rows[0] if comp_rows else {}

    # Running estimate
    re_rows = execute_query(
        "SELECT * FROM running_estimate WHERE run_date = %s", (run_date,)
    )
    data["running_estimate"] = re_rows[0] if re_rows else {}

    return data


def _build_reporter_prompt(data: dict) -> str:
    """Build the user prompt for the reporter LLM."""
    parts = [f"Run Date: {data['run_date']}, Cycle: Day {data.get('cycle_number', '?')}"]
    parts.append(
        f"Collection: {data.get('total_items', 0)} items "
        f"(HIGH: {data.get('high_count', 0)}, MED: {data.get('med_count', 0)}, "
        f"SIRs: {data.get('sir_count', 0)})"
    )

    # Composite metrics
    comp = data.get("composite", {})
    if comp:
        parts.append(
            f"\nMETRICS: Alert Level: {comp.get('alert_level', 'N/A')}, "
            f"Anomalous: {comp.get('anomalous_count', 0)}/{comp.get('total_collected', 0)}"
        )

    # Running estimate
    re = data.get("running_estimate", {})
    if re:
        parts.append(f"\nRUNNING ESTIMATE:\n{re.get('event_summary', 'N/A')}")
        parts.append(f"Trajectory: {re.get('trajectory', 'N/A')}")
        parts.append(f"Delta: {re.get('delta_notes', 'N/A')}")

    # Group outputs
    for gid in range(1, 7):
        grp = data.get(f"group_{gid}", {})
        synthesis = grp.get("synthesis_text", grp.get("assessment_json", "N/A"))
        if isinstance(synthesis, str) and len(synthesis) > 2000:
            synthesis = synthesis[:2000] + "..."
        parts.append(f"\nGROUP {gid} SYNTHESIS:\n{synthesis}")

    return "\n".join(parts)


def _parse_report_sections(llm_output: str, data: dict) -> dict:
    """Parse LLM output into template variables."""
    # The LLM produces HTML fragments for each section
    # We pass through directly, with data-driven fields filled in
    template_vars = {
        "run_date": data["run_date"],
        "cycle_number": data.get("cycle_number", "?"),
        "total_items": data.get("total_items", 0),
        "high_count": data.get("high_count", 0),
        "med_count": data.get("med_count", 0),
        "sir_count": data.get("sir_count", 0),
        "next_date": data.get("next_date", ""),
    }

    # Split LLM output by section markers or use as single block
    # The reporter LLM is instructed to output HTML fragments
    sections = _split_sections(llm_output)
    template_vars.update(sections)

    return template_vars


def _split_sections(text: str) -> dict:
    """Split reporter output into named sections."""
    section_map = {
        "EXECUTIVE SUMMARY": "executive_summary",
        "DIFF SUMMARY": "diff_summary",
        "PIR TRAJECTORY": "pir_trajectory_section",
        "SIGACTS": "sigacts_table",
        "PIR 1": "pir1_content",
        "PIR 2": "pir2_content",
        "PIR 3": "pir3_content",
        "PIR 4": "pir4_content",
        "BLACK SWAN": "black_swan_content",
        "BIG QUESTION": "big_question_content",
        "METRICS": "metrics_trend_section",
    }

    result = {}
    current_key = None
    current_lines = []

    for line in text.split("\n"):
        matched = False
        for marker, key in section_map.items():
            if marker in line.upper() and ":" in line:
                if current_key:
                    result[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = []
                matched = True
                break
        if not matched:
            current_lines.append(line)

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    # If no sections detected, use full text as executive summary
    if not result:
        result["executive_summary"] = text

    # Fill missing sections with defaults
    for key in section_map.values():
        if key not in result:
            result[key] = ""

    return result


# ── Template Rendering ────────────────────────────────────────────────

def _render_template(template_name: str, variables: dict) -> str:
    """Render a Jinja2 HTML template."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,  # We trust our own HTML output
    )
    template = env.get_template(template_name)
    return template.render(**variables)


def _store_report_archive(run_date: str, data: dict, html: str):
    """Store report metadata in report_archive."""
    re = data.get("running_estimate", {})
    trajectory = re.get("trajectory", "")
    if isinstance(trajectory, dict):
        trajectory = json.dumps(trajectory)

    comp = data.get("composite", {})
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO report_archive
                   (run_date, cycle_number, total_items, high_count, med_count,
                    alert_level, anomalous_metric_count, trajectory, html_length)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   cycle_number = VALUES(cycle_number),
                   total_items = VALUES(total_items),
                   high_count = VALUES(high_count),
                   med_count = VALUES(med_count),
                   alert_level = VALUES(alert_level),
                   trajectory = VALUES(trajectory),
                   html_length = VALUES(html_length)""",
            (
                run_date,
                data.get("cycle_number", 0),
                data.get("total_items", 0),
                data.get("high_count", 0),
                data.get("med_count", 0),
                comp.get("alert_level", "NORMAL"),
                comp.get("anomalous_count", 0),
                trajectory,
                len(html),
            ),
        )
