"""
SENTINEL2 — Database Seed Script
Seeds PIRs, metrics registry, collection plan, and email recipients.

Usage:
    python -m src.db.seed
"""

import logging
from pathlib import Path

import yaml

from src.db.connection import get_cursor, check_connection
from src.utils.config import get_config, get_project_root

logger = logging.getLogger("sentinel2.seed")


def seed_pirs():
    """Seed the pirs table with PIR definitions."""
    pirs = [
        ("PIR1", "Instability Drivers — Greater Middle East",
         "Catalysts, gray-zone escalation, and structural drivers of instability "
         "across the Greater Middle East", 1, False),
        ("PIR2", "Global Security Impact and Force Deployment Triggers",
         "Strategic implications for global security, NATO/U.S. force posture, "
         "and deployment trigger assessment", 2, False),
        ("PIR3", "Stabilizing Forces and De-escalation Indicators",
         "Diplomatic progress, reduction in operational tempo, economic "
         "normalization, and international stabilization measures", 3, True),
        ("PIR4", "Great Power Competition and Third-Party Conflict Shaping",
         "Russian diplomatic cover, Chinese economic enabling, and Sino-Russian "
         "strategic coordination in the ME/Caucasus", 4, True),
    ]

    sql = """
        INSERT INTO pirs (pir_id, pir_title, description, priority, is_ai_defined)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            pir_title = VALUES(pir_title),
            description = VALUES(description),
            priority = VALUES(priority),
            is_ai_defined = VALUES(is_ai_defined)
    """
    with get_cursor() as cursor:
        for pir in pirs:
            cursor.execute(sql, pir)
    logger.info(f"Seeded {len(pirs)} PIRs")


def seed_metrics():
    """Seed the metrics table from metrics_seed.yaml."""
    metrics_path = get_project_root() / "config" / "metrics_seed.yaml"
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sql = """
        INSERT INTO metrics
            (metric_id, name, domain, source, tier, collection_fn,
             baseline_window, alert_threshold, direction, enabled, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            domain = VALUES(domain),
            source = VALUES(source),
            tier = VALUES(tier),
            collection_fn = VALUES(collection_fn),
            notes = VALUES(notes)
    """

    with get_cursor() as cursor:
        for m in data["metrics"]:
            cursor.execute(sql, (
                m["id"], m["name"], m["domain"], m["source"],
                m.get("tier", 1), m.get("collection_fn", ""),
                m.get("baseline_window", 90), m.get("alert_threshold", 2.0),
                m.get("direction", "both"), True,
                m.get("notes", ""),
            ))
    logger.info(f"Seeded {len(data['metrics'])} metrics")


def seed_collection_plan():
    """Seed initial collection queries from config."""
    config = get_config()
    seed_queries = config.get("initialization", {}).get("seed_queries", [])

    sql = """
        INSERT INTO collection_plan (query_text, query_type, pir_id, sir_id, priority, source)
        VALUES (%s, %s, %s, %s, %s, 'seed')
        ON DUPLICATE KEY UPDATE query_text = VALUES(query_text)
    """

    with get_cursor() as cursor:
        for q in seed_queries:
            cursor.execute(sql, (
                q["query"],
                q.get("query_type", "gdelt_doc"),
                q["pir"],
                q.get("sir", ""),
                q.get("priority", 5),
            ))
    logger.info(f"Seeded {len(seed_queries)} collection queries")


def seed_email_recipients():
    """Seed default email recipients."""
    recipients = [
        ("preston.dihle@gmail.com", "Preston Dihle", "admin", "daily,weekly,monthly,black_swan"),
    ]

    sql = """
        INSERT INTO email_recipients (email, name, role, report_types)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            role = VALUES(role)
    """

    with get_cursor() as cursor:
        for r in recipients:
            cursor.execute(sql, r)
    logger.info(f"Seeded {len(recipients)} email recipients")


def run_schema():
    """Execute the full DDL schema script."""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    from src.db.connection import execute_script
    execute_script(sql_script)
    logger.info("Schema DDL executed")


def seed_all():
    """Run full seed: schema DDL + all data."""
    logger.info("Starting SENTINEL2 database seed...")

    if not check_connection():
        logger.error("Cannot connect to database. Aborting seed.")
        return False

    run_schema()
    seed_pirs()
    seed_metrics()
    seed_collection_plan()
    seed_email_recipients()

    logger.info("SENTINEL2 database seed complete")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv
    load_dotenv()
    seed_all()
