"""
SENTINEL2 — Pipeline Orchestrator
Main entry point for daily pipeline execution.
Implements the 16-step execution flow with checkpoint/resume support.

Usage:
    python -m src.pipeline                    # Full daily run
    python -m src.pipeline --resume           # Resume from last checkpoint
    python -m src.pipeline --date 2026-03-28  # Specific date
    python -m src.pipeline --step 10          # Run single step
    python -m src.pipeline --from-step 7      # Start from step 7
"""

import argparse
import json
import logging
import sys
import time
from datetime import date, timedelta
from typing import Optional

from src.db.connection import init_pool, get_cursor, execute_query
from src.utils.config import get_config

logger = logging.getLogger("sentinel2.pipeline")

# ── Pipeline Step Definitions ─────────────────────────────────────────

PIPELINE_STEPS = [
    {"step": 1,  "name": "cma",                "desc": "CMA Agent — collection plan management"},
    {"step": 2,  "name": "gdelt_collection",    "desc": "GDELT Collection — DOC + GKG + GEO"},
    {"step": 3,  "name": "supplementary",       "desc": "Supplementary Collection — scrapes, RSS, Telegram"},
    {"step": 4,  "name": "metrics_collection",  "desc": "Metrics Collection — 30 quantitative metrics"},
    {"step": 5,  "name": "processor",           "desc": "Processor — PIR/SIR mapping + significance"},
    {"step": 6,  "name": "metrics_scorer",      "desc": "Metrics Scorer — z-scores + anomaly detection"},
    {"step": 7,  "name": "running_estimate",    "desc": "Running Estimate — daily trajectory synthesis"},
    {"step": 8,  "name": "summarizer",          "desc": "Weekly/Monthly Summarizer (conditional)"},
    {"step": 9,  "name": "context_loader",      "desc": "Context Loader — assemble analyst context"},
    {"step": 10, "name": "analysis_groups",     "desc": "Analysis Groups 1-5 — Tree of Thought"},
    {"step": 11, "name": "black_swan_check",    "desc": "Black Swan Alert Check"},
    {"step": 12, "name": "big_question",        "desc": "Analysis Group 6 — Big Question (Opus)"},
    {"step": 13, "name": "reporter",            "desc": "Reporter — HTML generation"},
    {"step": 14, "name": "disseminate",         "desc": "Disseminate — PDF + Drive + Email"},
    {"step": 15, "name": "planner",             "desc": "Planner — tomorrow's collection plan"},
    {"step": 16, "name": "completion",          "desc": "Log completion, clear checkpoint"},
]


def run_pipeline(
    run_date: Optional[str] = None,
    resume: bool = False,
    single_step: Optional[int] = None,
    from_step: Optional[int] = None,
) -> dict:
    """
    Execute the full daily pipeline.

    Args:
        run_date: ISO date string. Defaults to today.
        resume: If True, skip already-completed steps.
        single_step: If set, run only this step.
        from_step: If set, start from this step number.

    Returns summary dict.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"{'='*60}")
    logger.info(f"SENTINEL2 Pipeline — {run_date}")
    logger.info(f"{'='*60}")

    # Initialize database pool
    init_pool()

    # Determine which steps to run
    completed_steps = set()
    if resume:
        completed_steps = _get_completed_steps(run_date)
        if completed_steps:
            logger.info(f"Resuming — {len(completed_steps)} steps already complete")

    results = {}
    pipeline_start = time.time()

    for step_def in PIPELINE_STEPS:
        step_num = step_def["step"]
        step_name = step_def["name"]

        # Skip logic
        if single_step is not None and step_num != single_step:
            continue
        if from_step is not None and step_num < from_step:
            continue
        if step_name in completed_steps:
            logger.info(f"Step {step_num}: {step_def['desc']} — SKIPPED (completed)")
            results[step_name] = {"status": "skipped"}
            continue

        # Execute step
        logger.info(f"Step {step_num}: {step_def['desc']} — STARTING")
        step_start = time.time()

        try:
            result = _execute_step(step_num, step_name, run_date, results)
            elapsed = time.time() - step_start
            result["elapsed_seconds"] = round(elapsed, 1)
            results[step_name] = result

            _save_checkpoint(run_date, step_name, "completed", result)
            logger.info(
                f"Step {step_num}: {step_def['desc']} — COMPLETE ({elapsed:.1f}s)"
            )

        except Exception as e:
            elapsed = time.time() - step_start
            logger.error(f"Step {step_num}: {step_def['desc']} — FAILED: {e}")
            results[step_name] = {"status": "failed", "error": str(e)}
            _save_checkpoint(run_date, step_name, "failed", {"error": str(e)})

            # Continue pipeline on non-critical failures
            if step_num in (13, 14):  # Reporter/Disseminate failures are non-fatal
                logger.warning("Non-critical step failed — continuing pipeline")
            else:
                logger.error("Critical step failed — pipeline halted")
                break

    total_elapsed = time.time() - pipeline_start
    logger.info(f"Pipeline complete: {total_elapsed:.0f}s total")

    return {
        "run_date": run_date,
        "total_elapsed_seconds": round(total_elapsed, 1),
        "steps": results,
    }


# ── Step Execution Router ─────────────────────────────────────────────

def _execute_step(step_num: int, step_name: str, run_date: str, prior: dict) -> dict:
    """Route to the appropriate step implementation."""

    if step_num == 1:
        from src.agents.cma import run_cma
        return run_cma(run_date)

    elif step_num == 2:
        from src.collectors.gdelt_collector import run_gdelt_collection
        return run_gdelt_collection(run_date)

    elif step_num == 3:
        # Supplementary collection (RSS, Telegram, CMA-triggered scrapes)
        from src.tools.rss_feed import fetch_all_default_feeds
        from src.tools.telegram_monitor import fetch_default_channels
        rss = fetch_all_default_feeds()
        telegram = fetch_default_channels()
        return {
            "status": "ok",
            "rss_feeds": len(rss),
            "telegram_channels": len(telegram),
        }

    elif step_num == 4:
        from src.utils.metrics_scorer import collect_all_metrics
        return collect_all_metrics(run_date)

    elif step_num == 5:
        from src.agents.processor import run_processor
        return run_processor(run_date)

    elif step_num == 6:
        from src.utils.metrics_scorer import score_daily_metrics
        return score_daily_metrics(run_date)

    elif step_num == 7:
        from src.agents.running_estimate import run_running_estimate
        return run_running_estimate(run_date)

    elif step_num == 8:
        return _run_conditional_summarizer(run_date)

    elif step_num == 9:
        from src.agents.context_loader import build_analyst_context
        context = build_analyst_context(run_date)
        return {"status": "ok", "context_keys": list(context.keys())}

    elif step_num == 10:
        from src.agents.analysis_crew import run_analysis_groups
        # Run groups 1-5 only (group 6 is step 12)
        return _run_groups_1_to_5(run_date)

    elif step_num == 11:
        return _run_black_swan_check(run_date, prior)

    elif step_num == 12:
        from src.agents.analysis_crew import run_single_group
        return run_single_group(6, run_date)

    elif step_num == 13:
        from src.agents.reporter import generate_daily_report
        return generate_daily_report(run_date)

    elif step_num == 14:
        return _run_dissemination(run_date, prior)

    elif step_num == 15:
        from src.agents.planner import run_planner
        return run_planner(run_date)

    elif step_num == 16:
        return _log_completion(run_date, prior)

    return {"status": "unknown_step"}


# ── Step Implementations ──────────────────────────────────────────────

def _run_conditional_summarizer(run_date: str) -> dict:
    """Run weekly (Sunday) and monthly (1st) summarizers conditionally."""
    from src.agents.summarizer import run_weekly_summary, run_monthly_summary

    rd = date.fromisoformat(run_date)
    result = {"status": "ok"}

    # Weekly: run on Sundays (weekday 6)
    if rd.weekday() == 6:
        logger.info("Sunday — running weekly summary")
        result["weekly"] = run_weekly_summary(run_date)
    else:
        result["weekly"] = {"status": "skipped", "reason": "not_sunday"}

    # Monthly: run on 1st of month
    if rd.day == 1:
        logger.info("1st of month — running monthly summary")
        result["monthly"] = run_monthly_summary(run_date)
    else:
        result["monthly"] = {"status": "skipped", "reason": "not_1st"}

    return result


def _run_groups_1_to_5(run_date: str) -> dict:
    """Run analysis groups 1-5 (not group 6)."""
    from src.agents.analysis_crew import run_single_group

    results = {}
    for gid in range(1, 6):
        try:
            results[f"group_{gid}"] = run_single_group(gid, run_date)
        except Exception as e:
            logger.error(f"Group {gid} failed: {e}")
            results[f"group_{gid}"] = {"status": "failed", "error": str(e)}

    return {"status": "ok", "groups": results}


def _run_black_swan_check(run_date: str, prior: dict) -> dict:
    """Check Group 5 output for Black Swan triggers."""
    from src.agents.black_swan_alert import check_and_alert

    # Get Group 5 output from step 10
    group5_output = {}
    analysis_result = prior.get("analysis_groups", {})
    if isinstance(analysis_result, dict):
        groups = analysis_result.get("groups", {})
        group5_output = groups.get("group_5", {})

    result = check_and_alert(group5_output, run_date)

    # If alert triggered, generate and disseminate alert report
    if result.get("alert_triggered"):
        from src.agents.reporter import generate_black_swan_report
        from src.agents.pdf_renderer import render_black_swan_report
        from src.agents.disseminate import disseminate_black_swan_alert

        for alert in result.get("alerts", []):
            try:
                bsa_report = generate_black_swan_report(
                    {"alert_summary": alert[:500] if isinstance(alert, str) else ""},
                    run_date,
                )
                if bsa_report.get("html_path"):
                    pdf_path = render_black_swan_report(bsa_report["html_path"])
                    if pdf_path:
                        disseminate_black_swan_alert(run_date, pdf_path)
            except Exception as e:
                logger.error(f"Black Swan alert dispatch failed: {e}")

    return result


def _run_dissemination(run_date: str, prior: dict) -> dict:
    """Render PDF and disseminate the daily report."""
    from src.agents.pdf_renderer import render_daily_report
    from src.agents.disseminate import disseminate_report

    reporter_result = prior.get("reporter", {})
    html_path = reporter_result.get("html_path", "")

    if not html_path:
        return {"status": "skipped", "reason": "no_html_report"}

    # Render PDF
    pdf_path = render_daily_report(run_date)
    if not pdf_path:
        return {"status": "failed", "reason": "pdf_render_failed"}

    # Disseminate
    return disseminate_report(run_date, pdf_path, "daily")


def _log_completion(run_date: str, prior: dict) -> dict:
    """Log pipeline completion."""
    logger.info(f"Pipeline run complete for {run_date}")
    return {"status": "completed", "run_date": run_date}


# ── Checkpoint System ─────────────────────────────────────────────────

def _save_checkpoint(run_date: str, step_name: str, status: str, result: dict):
    """Save a pipeline checkpoint to the database."""
    try:
        # Truncate result for storage
        result_json = json.dumps(result, default=str)
        if len(result_json) > 10000:
            result_json = json.dumps({"status": result.get("status", status)})

        with get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO pipeline_checkpoints
                       (run_date, step_name, status, results)
                   VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                       status = VALUES(status),
                       results = VALUES(results),
                       completed_at = NOW()""",
                (run_date, step_name, status, result_json),
            )
    except Exception as e:
        logger.warning(f"Checkpoint save failed: {e}")


def _get_completed_steps(run_date: str) -> set:
    """Get set of completed step names for resume support."""
    try:
        rows = execute_query(
            """SELECT step_name FROM pipeline_checkpoints
               WHERE run_date = %s AND status = 'completed'""",
            (run_date,),
        )
        return {r["step_name"] for r in rows}
    except Exception:
        return set()


# ── CLI Entry Point ───────────────────────────────────────────────────

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="SENTINEL2 Pipeline Orchestrator")
    parser.add_argument(
        "--date", type=str, default=None,
        help="Run date (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--step", type=int, default=None,
        help="Run a single step (1-16)",
    )
    parser.add_argument(
        "--from-step", type=int, default=None,
        help="Start from this step number",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    result = run_pipeline(
        run_date=args.date,
        resume=args.resume,
        single_step=args.step,
        from_step=args.from_step,
    )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
