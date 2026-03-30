"""
SENTINEL2 — Collection Manager Agent (CMA)
Tool-equipped CrewAI Agent that optimizes daily intelligence collection.
Uses Claude Sonnet for strategic judgment.

CMA Decision Authority:
  - Retire low-yield queries
  - Promote high-significance sources
  - Add new collection targets when gaps detected
  - Update AI-defined PIRs 3 & 4 based on analyst group feedback
  - Trigger supplementary scraping when a critical story needs full text
  - Recommend expert rotation from reserve pool
"""

import json
import logging
from datetime import date
from typing import Optional

from crewai import Agent, Crew, Task, Process, LLM

from src.tools.gdelt_doc import GDELTDocSearchTool
from src.tools.gdelt_gkg import GDELTGKGTool
from src.tools.web_scrape import WebScrapeTool
from src.tools.web_search import WebSearchTool, GoogleNewsTool
from src.tools.rss_feed import RSSFeedTool
from src.tools.telegram_monitor import TelegramMonitorTool
from src.tools.mysql_query import MySQLQueryTool

from src.db.connection import execute_query, get_cursor
from src.utils.llm import call_llm_json
from src.agents.context_loader import load_task_prompt

logger = logging.getLogger("sentinel2.cma")

_CMA_LLM = "anthropic/claude-sonnet-4-20250514"


def create_cma_agent() -> Agent:
    """Create the CMA as a tool-equipped CrewAI Agent."""
    return Agent(
        role="Collection Manager",
        goal=(
            "Optimize daily intelligence collection to maximize PIR coverage, "
            "identify emerging gaps, retire low-yield queries, and ensure the "
            "collection plan evolves to track the changing threat landscape."
        ),
        backstory=(
            "Senior collection manager with 20 years of OSINT experience across "
            "the Greater Middle East. Expert in managing large-scale automated "
            "collection programs, balancing breadth of coverage against depth of "
            "insight. Known for anticipating where the next critical story will "
            "emerge and redirecting collection assets proactively. Fluent in GDELT "
            "query optimization, RSS feed management, and multi-source correlation."
        ),
        llm=LLM(model=_CMA_LLM),
        tools=[
            GDELTDocSearchTool(),
            GDELTGKGTool(),
            WebScrapeTool(),
            WebSearchTool(),
            GoogleNewsTool(),
            RSSFeedTool(),
            TelegramMonitorTool(),
            MySQLQueryTool(),
        ],
        memory=True,
        verbose=True,
    )


def run_cma(run_date: Optional[str] = None) -> dict:
    """
    Execute the CMA for a daily collection management cycle.

    Steps:
      1. Assess current collection plan yield
      2. Evaluate PIR coverage gaps
      3. Make retirement/promotion/addition decisions
      4. Update AI-defined PIRs 3 & 4 if warranted
      5. Write tomorrow's collection plan

    Returns CMA decision output dict.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"CMA cycle starting for {run_date}")

    # Build CMA context
    context = _build_cma_context(run_date)
    system_prompt = load_task_prompt("cma.txt")

    # Use LLM-driven approach for CMA decisions
    result = call_llm_json(
        prompt=context,
        system_prompt=system_prompt,
        component="cma",
    )

    if not result:
        logger.error("CMA LLM call returned empty result")
        return {"status": "failed", "run_date": run_date}

    # Execute CMA decisions
    _execute_collection_plan(result.get("collection_plan", []))
    _execute_retirements(result.get("retired_queries", []))
    _update_ai_pirs(result)
    _log_cma_decisions(result)

    logger.info(
        f"CMA cycle complete: {len(result.get('collection_plan', []))} queries planned, "
        f"{len(result.get('retired_queries', []))} retired"
    )
    return result


# ── Context Building ──────────────────────────────────────────────────

def _build_cma_context(run_date: str) -> str:
    """Build the user prompt with all CMA-relevant context."""
    parts = [f"Run Date: {run_date}\n"]

    # Active query yield metrics
    active_queries = execute_query(
        """SELECT query_id, query_text, pir_id, sir_id, priority,
                  last_yield, low_yield_days, total_runs, total_results
           FROM collection_plan WHERE status = 'active'
           ORDER BY priority"""
    )
    parts.append(f"ACTIVE COLLECTION PLAN ({len(active_queries)} queries):")
    for q in active_queries:
        parts.append(
            f"  [{q['query_id']}] PIR:{q.get('pir_id','?')} SIR:{q.get('sir_id','?')} "
            f"Priority:{q.get('priority',5)} | "
            f"Last yield:{q.get('last_yield',0)} Low-yield days:{q.get('low_yield_days',0)} | "
            f"Total runs:{q.get('total_runs',0)} Total results:{q.get('total_results',0)}\n"
            f"    Query: {q.get('query_text','')}"
        )

    # Today's collection stats
    stats = execute_query(
        """SELECT pir_id, significance, COUNT(*) as cnt
           FROM processed_collection
           WHERE run_date = %s
           GROUP BY pir_id, significance""",
        (run_date,),
    )
    parts.append(f"\nTODAY'S COLLECTION SUMMARY:")
    for s in stats:
        parts.append(
            f"  PIR {s.get('pir_id','?')}: {s.get('cnt',0)} items "
            f"({s.get('significance','?')})"
        )

    # Anomalous metrics
    anomalies = execute_query(
        """SELECT m.name, m.domain, d.z_score, d.trend_7d
           FROM daily_values d
           JOIN metrics m ON d.metric_id = m.metric_id
           WHERE d.run_date = %s AND d.anomaly_flag = TRUE""",
        (run_date,),
    )
    if anomalies:
        parts.append(f"\nANOMALOUS METRICS ({len(anomalies)}):")
        for a in anomalies:
            parts.append(
                f"  {a.get('name')} ({a.get('domain')}): "
                f"z={a.get('z_score','?')}, trend={a.get('trend_7d','?')}"
            )

    # Current PIR 3 & 4 text
    pirs = execute_query(
        "SELECT pir_id, pir_title, description FROM pirs WHERE pir_id IN ('PIR3', 'PIR4')"
    )
    parts.append("\nCURRENT AI-DEFINED PIRs:")
    for p in pirs:
        parts.append(f"  {p.get('pir_id')}: {p.get('pir_title')}")
        parts.append(f"    {p.get('description', 'N/A')}")

    # Recent CMA log
    recent_log = execute_query(
        "SELECT timestamp, action, details FROM cma_log ORDER BY timestamp DESC LIMIT 10"
    )
    if recent_log:
        parts.append("\nRECENT CMA DECISIONS:")
        for entry in recent_log:
            parts.append(
                f"  [{entry.get('timestamp')}] {entry.get('action')}: "
                f"{entry.get('details','')[:100]}"
            )

    return "\n".join(parts)


# ── Decision Execution ────────────────────────────────────────────────

def _execute_collection_plan(plan: list):
    """Write new collection plan queries to the database."""
    for item in plan:
        query_text = item.get("query_text", item.get("query", ""))
        if not query_text:
            continue
        with get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO collection_plan
                       (query_text, query_type, pir_id, sir_id, priority, source)
                   VALUES (%s, %s, %s, %s, %s, 'cma')
                   ON DUPLICATE KEY UPDATE
                       priority = VALUES(priority),
                       status = 'active'""",
                (
                    query_text,
                    item.get("query_type", "gdelt_doc"),
                    item.get("pir_id"),
                    item.get("sir_id"),
                    item.get("priority", 5),
                ),
            )


def _execute_retirements(retired: list):
    """Retire queries flagged by the CMA."""
    for item in retired:
        query_id = item.get("query_id")
        if query_id is None:
            continue
        with get_cursor() as cursor:
            cursor.execute(
                """UPDATE collection_plan
                   SET status = 'retired', retired_at = NOW()
                   WHERE query_id = %s""",
                (query_id,),
            )
            logger.info(f"Retired query {query_id}: {item.get('reason', '')}")


def _update_ai_pirs(result: dict):
    """Update AI-defined PIRs 3 & 4 if CMA provides new text."""
    for pir_key, field in [("PIR3", "pir3_updated"), ("PIR4", "pir4_updated")]:
        new_text = result.get(field)
        if new_text and isinstance(new_text, str) and len(new_text) > 10:
            with get_cursor() as cursor:
                cursor.execute(
                    """UPDATE pirs SET description = %s,
                           updated_at = NOW()
                       WHERE pir_id = %s AND is_ai_defined = TRUE""",
                    (new_text, pir_key),
                )
            logger.info(f"CMA updated {pir_key} definition")


def _log_cma_decisions(result: dict):
    """Log CMA decisions to cma_log table."""
    rationale = result.get("rationale_log", [])
    for entry in rationale:
        action = entry if isinstance(entry, str) else entry.get("action", "decision")
        details = entry if isinstance(entry, str) else entry.get("details", str(entry))
        with get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO cma_log (action, details)
                   VALUES (%s, %s)""",
                (action[:50], details[:500]),
            )
