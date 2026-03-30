"""
SENTINEL2 — Collection Planner Agent
Produces tomorrow's collection plan based on today's report,
yield data, and analysis group recommendations.
Uses Claude Sonnet for strategic planning.
"""

import json
import logging
from datetime import date
from typing import Optional

from src.db.connection import execute_query, get_cursor
from src.utils.llm import call_llm_json
from src.agents.context_loader import load_task_prompt

logger = logging.getLogger("sentinel2.planner")


def run_planner(run_date: Optional[str] = None) -> dict:
    """
    Generate tomorrow's collection plan.

    Reads today's intelligence output, collection yield data, and
    analysis group recommendations to produce an optimized plan.

    Returns the planner output dict with new queries and retirements.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"Running planner for {run_date}")

    system_prompt = load_task_prompt("planner.txt")
    user_prompt = _build_planner_context(run_date)

    result = call_llm_json(
        system_prompt=system_prompt,
        prompt=user_prompt,
        component="planner",  # Claude Sonnet
    )

    if not result:
        logger.error("Planner LLM returned empty")
        return {"status": "failed", "run_date": run_date}

    # Execute planner decisions
    new_queries = result.get("queries", result.get("collection_plan", []))
    retired = result.get("retire", result.get("retired_queries", []))

    _add_planned_queries(new_queries)
    _retire_planned_queries(retired)
    _log_planner_output(run_date, result)

    logger.info(
        f"Planner complete: {len(new_queries)} new queries, "
        f"{len(retired)} retirements"
    )
    return result


# ── Context Building ──────────────────────────────────────────────────

def _build_planner_context(run_date: str) -> str:
    """Build user prompt with planner-relevant context."""
    parts = [f"Run Date: {run_date}\n"]

    # Current collection plan with yield
    queries = execute_query(
        """SELECT query_id, query_text, pir_id, sir_id, priority,
                  last_yield, low_yield_days, total_runs, total_results
           FROM collection_plan WHERE status = 'active'
           ORDER BY priority, pir_id"""
    )
    parts.append(f"ACTIVE COLLECTION PLAN ({len(queries)} queries):")
    for q in queries:
        parts.append(
            f"  [{q['query_id']}] P{q.get('priority',5)} "
            f"PIR:{q.get('pir_id','?')} SIR:{q.get('sir_id','?')} "
            f"yield:{q.get('last_yield',0)} low_days:{q.get('low_yield_days',0)} "
            f"runs:{q.get('total_runs',0)} total:{q.get('total_results',0)}\n"
            f"    {q.get('query_text','')}"
        )

    # Collection gaps from analysis groups
    for gid in range(1, 7):
        rows = execute_query(
            """SELECT assessment_json FROM ae_assessments
               WHERE group_id = %s AND run_date = %s
               ORDER BY created_at DESC LIMIT 1""",
            (gid, run_date),
        )
        if rows:
            try:
                assessment = json.loads(rows[0].get("assessment_json", "{}"))
                gaps = assessment.get("collection_gaps", assessment.get("recommended_collection", ""))
                if gaps:
                    parts.append(f"\nGROUP {gid} COLLECTION GAPS: {gaps}")
            except (json.JSONDecodeError, TypeError):
                pass

    # Running estimate trajectory
    re_rows = execute_query(
        "SELECT trajectory, delta_notes FROM running_estimate WHERE run_date = %s",
        (run_date,),
    )
    if re_rows:
        parts.append(f"\nTRAJECTORY: {re_rows[0].get('trajectory', 'N/A')}")
        parts.append(f"DELTA: {re_rows[0].get('delta_notes', 'N/A')}")

    # Anomalous metrics
    anomalies = execute_query(
        """SELECT m.name, m.domain, d.z_score
           FROM daily_values d JOIN metrics m ON d.metric_id = m.metric_id
           WHERE d.run_date = %s AND d.anomaly_flag = TRUE""",
        (run_date,),
    )
    if anomalies:
        parts.append(f"\nANOMALOUS METRICS ({len(anomalies)}):")
        for a in anomalies:
            parts.append(f"  {a['name']} ({a['domain']}): z={a.get('z_score','?')}")

    return "\n".join(parts)


# ── Decision Execution ────────────────────────────────────────────────

def _add_planned_queries(queries: list):
    """Add new collection queries from planner output."""
    for q in queries:
        query_text = q.get("query", q.get("query_string", q.get("query_text", "")))
        if not query_text:
            continue
        with get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO collection_plan
                       (query_text, query_type, pir_id, sir_id, priority, source)
                   VALUES (%s, 'gdelt_doc', %s, %s, %s, 'planner')""",
                (
                    query_text,
                    q.get("pir_id", q.get("pir")),
                    q.get("sir_id", q.get("sir")),
                    q.get("priority", 5),
                ),
            )


def _retire_planned_queries(retired: list):
    """Retire queries flagged by planner."""
    for item in retired:
        qid = item.get("query_id", item.get("id"))
        if qid is None:
            continue
        with get_cursor() as cursor:
            cursor.execute(
                """UPDATE collection_plan
                   SET status = 'retired', retired_at = NOW()
                   WHERE query_id = %s""",
                (qid,),
            )


def _log_planner_output(run_date: str, result: dict):
    """Log planner decisions to cma_log."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO cma_log (action, details)
               VALUES ('planner_cycle', %s)""",
            (json.dumps(result, default=str)[:2000],),
        )
