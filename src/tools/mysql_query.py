"""
SENTINEL2 — MySQL Query Tool
CrewAI tool allowing the CMA to query the sentinel2 database
for collection plan metrics, yield data, and pipeline state.
"""

import json
import logging

from crewai.tools import BaseTool

from src.db.connection import execute_query

logger = logging.getLogger("sentinel2.tools.mysql_query")

# Read-only queries the CMA is allowed to run
_ALLOWED_QUERIES = {
    "active_queries": """
        SELECT query_id, query_text, pir_id, sir_id, priority,
               last_run, last_yield, low_yield_days, total_runs, total_results
        FROM collection_plan
        WHERE status = 'active'
        ORDER BY priority, query_id
    """,
    "low_yield": """
        SELECT query_id, query_text, pir_id, sir_id,
               low_yield_days, total_runs, total_results
        FROM collection_plan
        WHERE status = 'active' AND low_yield_days >= 3
        ORDER BY low_yield_days DESC
    """,
    "retired_queries": """
        SELECT query_id, query_text, pir_id, sir_id,
               retired_at, total_runs, total_results
        FROM collection_plan
        WHERE status = 'retired'
        ORDER BY retired_at DESC
        LIMIT 20
    """,
    "pir_coverage": """
        SELECT p.pir_id, p.pir_title,
               COUNT(cp.query_id) AS active_queries,
               SUM(cp.total_results) AS total_results
        FROM pirs p
        LEFT JOIN collection_plan cp ON p.pir_id = cp.pir_id AND cp.status = 'active'
        WHERE p.status = 'active'
        GROUP BY p.pir_id, p.pir_title
    """,
    "today_collection_stats": """
        SELECT pir_id, significance,
               COUNT(*) AS count
        FROM processed_collection
        WHERE run_date = CURDATE()
        GROUP BY pir_id, significance
        ORDER BY pir_id, significance
    """,
    "composite_score": """
        SELECT * FROM composite_scores
        WHERE run_date = CURDATE()
    """,
    "anomalous_metrics": """
        SELECT m.name, m.domain, d.raw_value, d.z_score, d.trend_7d
        FROM daily_values d
        JOIN metrics m ON d.metric_id = m.metric_id
        WHERE d.run_date = CURDATE() AND d.anomaly_flag = TRUE
    """,
    "cma_log_recent": """
        SELECT * FROM cma_log
        ORDER BY timestamp DESC
        LIMIT 20
    """,
}


class MySQLQueryTool(BaseTool):
    name: str = "Database Query Tool"
    description: str = (
        "Query the sentinel2 database for collection plan metrics and pipeline state. "
        "Available queries: active_queries, low_yield, retired_queries, pir_coverage, "
        "today_collection_stats, composite_score, anomalous_metrics, cma_log_recent. "
        "Pass the query name as input."
    )

    def _run(self, query_name: str) -> str:
        query_name = query_name.strip().lower()
        if query_name not in _ALLOWED_QUERIES:
            return (
                f"Unknown query: '{query_name}'. "
                f"Available: {', '.join(_ALLOWED_QUERIES.keys())}"
            )
        return run_cma_query(query_name)


def run_cma_query(query_name: str) -> str:
    """Execute a pre-defined CMA query and return formatted results."""
    sql = _ALLOWED_QUERIES.get(query_name)
    if not sql:
        return f"Unknown query: {query_name}"

    try:
        rows = execute_query(sql)
        if not rows:
            return f"Query '{query_name}': no results"
        return json.dumps(rows, indent=2, default=str)
    except Exception as e:
        logger.warning(f"CMA query '{query_name}' failed: {e}")
        return f"Query failed: {e}"
