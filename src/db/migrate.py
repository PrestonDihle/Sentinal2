"""
SENTINEL2 — Schema Migration Helper
Runs schema.sql against an existing database to apply new tables/columns.

Usage:
    python -m src.db.migrate
"""

import logging
from src.db.seed import run_schema
from src.db.connection import check_connection

logger = logging.getLogger("sentinel2.migrate")


def migrate():
    """Apply schema DDL (CREATE IF NOT EXISTS is idempotent)."""
    if not check_connection():
        logger.error("Cannot connect to MySQL")
        return False
    run_schema()
    logger.info("Migration complete")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv
    load_dotenv()
    migrate()
