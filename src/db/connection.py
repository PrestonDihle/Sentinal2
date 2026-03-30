"""
SENTINEL2 — SQLite Database Connection
Provides a thread-safe SQLite connection with the same interface
as the original MySQL pool layer. Single file, zero infrastructure.
"""

import os
import sqlite3
import logging
import threading
from typing import Optional
from contextlib import contextmanager
from pathlib import Path

from src.utils.config import get_config, get_project_root

logger = logging.getLogger("sentinel2.db")

_db_path: Optional[str] = None
_local = threading.local()


def _get_db_path() -> str:
    """Resolve the SQLite database file path."""
    global _db_path
    if _db_path:
        return _db_path

    config = get_config()
    db_cfg = config.get("database", {})
    rel_path = db_cfg.get("sqlite_path", "data/sentinel2.db")
    abs_path = get_project_root() / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    _db_path = str(abs_path)
    return _db_path


def _dict_factory(cursor, row):
    """Row factory that returns dicts instead of tuples."""
    fields = [col[0] for col in cursor.description]
    return dict(zip(fields, row))


def init_pool():
    """
    Initialize the database (SQLite equivalent of pool init).
    Creates the DB file if it doesn't exist. Call once at startup.
    """
    db_path = _get_db_path()
    logger.info(f"SQLite database: {db_path}")
    # Touch the file to ensure it exists
    Path(db_path).touch(exist_ok=True)
    return db_path


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = _dict_factory
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


@contextmanager
def get_connection():
    """Context manager that yields a SQLite connection."""
    conn = _get_conn()
    try:
        yield conn
    except Exception as e:
        logger.error(f"SQLite connection error: {e}")
        raise


class _TranslatingCursor:
    """Wrapper around SQLite cursor that auto-translates MySQL SQL."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        sql = _translate_sql(sql)
        if params:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def executemany(self, sql, data):
        sql = _translate_sql(sql)
        return self._cursor.executemany(sql, data)

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def close(self):
        return self._cursor.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description


@contextmanager
def get_cursor(dictionary: bool = True):
    """
    Context manager that yields a cursor (auto-commits, auto-closes).
    The dictionary parameter is accepted for API compatibility but
    SQLite always uses dict rows via row_factory.
    All SQL is auto-translated from MySQL to SQLite syntax.
    """
    conn = _get_conn()
    raw_cursor = conn.cursor()
    cursor = _TranslatingCursor(raw_cursor)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        raw_cursor.close()


def execute_query(sql: str, params: tuple = None, fetch: bool = True) -> list:
    """Execute a single query and return results (if fetch=True).
    Auto-commits for write operations (INSERT/UPDATE/DELETE)."""
    sql = _translate_sql(sql)
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        if fetch:
            return cursor.fetchall()
        # Commit writes (non-fetch implies mutation)
        conn.commit()
        return []
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def execute_many(sql: str, data: list[tuple]) -> int:
    """Execute a parameterized query for many rows. Returns row count."""
    sql = _translate_sql(sql)
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        cursor.executemany(sql, data)
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()


def execute_script(sql_script: str):
    """Execute a multi-statement SQL script (e.g., schema DDL)."""
    conn = _get_conn()
    try:
        conn.executescript(sql_script)
        logger.info("SQL script executed successfully")
    except Exception as e:
        logger.error(f"SQL script execution failed: {e}")
        raise


def check_connection() -> bool:
    """Verify SQLite connectivity."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"SQLite connection check failed: {e}")
        return False


def _translate_sql(sql: str) -> str:
    """
    Translate MySQL-specific SQL to SQLite-compatible SQL.
    Handles the most common differences.
    """
    # %s -> ? (parameter placeholder)
    sql = sql.replace("%s", "?")

    # ON DUPLICATE KEY UPDATE -> OR REPLACE / OR IGNORE
    # This is a rough translation — for INSERTs with ON DUPLICATE KEY
    if "ON DUPLICATE KEY UPDATE" in sql.upper():
        sql = _translate_upsert(sql)

    # CURDATE() -> date('now')
    sql = sql.replace("CURDATE()", "date('now')")
    sql = sql.replace("curdate()", "date('now')")

    # NOW() -> datetime('now')
    sql = sql.replace("NOW()", "datetime('now')")
    sql = sql.replace("now()", "datetime('now')")

    return sql


def _translate_upsert(sql: str) -> str:
    """
    Convert MySQL ON DUPLICATE KEY UPDATE to SQLite ON CONFLICT DO UPDATE.

    MySQL:   INSERT INTO t (a, b, c) VALUES (?, ?, ?)
             ON DUPLICATE KEY UPDATE b = VALUES(b), c = VALUES(c)

    SQLite:  INSERT INTO t (a, b, c) VALUES (?, ?, ?)
             ON CONFLICT DO UPDATE SET b = excluded.b, c = excluded.c

    Falls back to INSERT OR REPLACE if parsing fails.
    """
    import re

    upper = sql.upper()
    idx = upper.find("ON DUPLICATE KEY UPDATE")
    if idx == -1:
        return sql

    insert_part = sql[:idx].strip()
    update_part = sql[idx + len("ON DUPLICATE KEY UPDATE"):].strip()

    # Parse the UPDATE assignments: "col = VALUES(col), col2 = VALUES(col2)"
    # Convert VALUES(col) → excluded.col (SQLite syntax)
    if update_part:
        # Replace VALUES(colname) with excluded.colname
        converted = re.sub(
            r'VALUES\s*\(\s*(\w+)\s*\)',
            r'excluded.\1',
            update_part,
            flags=re.IGNORECASE,
        )
        # Also handle plain column references like "completed_at = NOW()"
        # (these don't use VALUES() so pass through unchanged)
        return f"{insert_part} ON CONFLICT DO UPDATE SET {converted}"

    # No update clause content — fall back to INSERT OR REPLACE
    if insert_part.upper().startswith("INSERT INTO"):
        return "INSERT OR REPLACE INTO" + insert_part[11:]
    return insert_part
