"""
SENTINEL2 — GDELT Collection Orchestrator
Orchestrates per-SIR GDELT queries, GKG bulk download, and GEO heatmap.
Writes results to raw_collection table.

This is the primary collection engine replacing DuckDuckGo from Sentinel v1.
"""

import json
import logging
from datetime import date, datetime
from typing import Optional

from src.tools.gdelt_doc import gdelt_doc_artlist
from src.tools.gdelt_gkg import download_gkg_range, filter_gkg_records
from src.tools.gdelt_geo import get_daily_heatmap
from src.collectors.gdelt_queries import SIR_QUERY_MAP, get_all_queries
from src.db.connection import get_cursor, execute_query
from src.utils.config import get_config

logger = logging.getLogger("sentinel2.collectors.gdelt")


def run_gdelt_collection(
    run_date: Optional[str] = None,
    skip_gkg: bool = False,
    skip_geo: bool = False,
) -> dict:
    """
    Execute the full GDELT collection pipeline for one day.

    Steps:
        1. DOC 2.0 queries per SIR
        2. GKG bulk download (optional)
        3. GEO heatmap (optional)

    Args:
        run_date: ISO date string (default: today)
        skip_gkg: Skip GKG bulk download
        skip_geo: Skip GEO heatmap

    Returns:
        Summary dict with counts and stats.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    config = get_config()
    max_articles = config.get("gdelt", {}).get("max_articles_per_query", 250)

    stats = {
        "run_date": run_date,
        "doc_queries_run": 0,
        "doc_articles_collected": 0,
        "doc_articles_stored": 0,
        "gkg_records": 0,
        "geo_points": 0,
        "errors": [],
    }

    # ── Step 1: DOC 2.0 per-SIR queries ──────────────────────────────
    logger.info(f"Starting GDELT DOC collection for {run_date}")
    all_queries = get_all_queries()

    for q_entry in all_queries:
        sir_id = q_entry["sir_id"]
        pir_id = q_entry["pir_id"]
        query_text = q_entry["query"]
        theme = q_entry.get("theme")
        sourcecountry = q_entry.get("sourcecountry")

        try:
            articles = gdelt_doc_artlist(
                query=query_text,
                timespan="1d",
                maxrecords=max_articles,
                sourcecountry=sourcecountry,
                theme=theme,
            )
            stats["doc_queries_run"] += 1
            stats["doc_articles_collected"] += len(articles)

            # Store each article in raw_collection
            stored = _store_articles(
                articles=articles,
                query_text=query_text,
                pir_id=pir_id,
                sir_id=sir_id,
                run_date=run_date,
            )
            stats["doc_articles_stored"] += stored

            logger.info(
                f"  SIR {sir_id}: '{query_text[:50]}...' → "
                f"{len(articles)} articles, {stored} stored"
            )
        except Exception as e:
            logger.warning(f"  SIR {sir_id} query failed: {e}")
            stats["errors"].append({"sir_id": sir_id, "error": str(e)})

    # ── Step 2: GKG bulk download ─────────────────────────────────────
    if not skip_gkg:
        logger.info("Starting GKG bulk download (last 24h)")
        try:
            raw_gkg = download_gkg_range(hours_back=24, max_files=48)
            filtered_gkg = filter_gkg_records(raw_gkg)
            stats["gkg_records"] = len(filtered_gkg)

            # Store GKG records as raw_collection items
            gkg_stored = _store_gkg_records(filtered_gkg, run_date)
            logger.info(f"GKG: {len(raw_gkg)} raw → {len(filtered_gkg)} filtered → {gkg_stored} stored")
        except Exception as e:
            logger.warning(f"GKG collection failed: {e}")
            stats["errors"].append({"step": "gkg", "error": str(e)})
    else:
        logger.info("Skipping GKG bulk download")

    # ── Step 3: GEO heatmap ───────────────────────────────────────────
    if not skip_geo:
        logger.info("Generating daily GEO heatmap")
        try:
            heatmap = get_daily_heatmap(date_str=run_date)
            stats["geo_points"] = heatmap.get("total_unique_points", 0)
            logger.info(f"GEO heatmap: {stats['geo_points']} unique points")
        except Exception as e:
            logger.warning(f"GEO heatmap failed: {e}")
            stats["errors"].append({"step": "geo", "error": str(e)})
    else:
        logger.info("Skipping GEO heatmap")

    # ── Summary ───────────────────────────────────────────────────────
    logger.info(
        f"GDELT collection complete: "
        f"{stats['doc_queries_run']} queries, "
        f"{stats['doc_articles_stored']} articles stored, "
        f"{stats['gkg_records']} GKG records, "
        f"{stats['geo_points']} GEO points, "
        f"{len(stats['errors'])} errors"
    )
    return stats


def _store_articles(
    articles: list[dict],
    query_text: str,
    pir_id: str,
    sir_id: str,
    run_date: str,
) -> int:
    """
    Store GDELT DOC articles into raw_collection table.
    Skips duplicates via ON DUPLICATE KEY.

    Returns:
        Number of rows actually inserted.
    """
    if not articles:
        return 0

    # Look up query_id from collection_plan (or None)
    query_id = _get_query_id(query_text, pir_id, sir_id)

    sql = """
        INSERT INTO raw_collection
            (query_id, collection_date, source_url, source_name, title,
             snippet, gdelt_themes, gdelt_tone, gdelt_entities, gdelt_locations,
             pir_id, sir_id, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE title = VALUES(title)
    """

    stored = 0
    with get_cursor() as cursor:
        for art in articles:
            try:
                url = art.get("url", "")
                if not url:
                    continue

                title = art.get("title", "")[:512]
                domain = art.get("domain", "")
                tone = art.get("tone", 0.0)
                # GDELT DOC artlist doesn't include themes/entities directly
                # Those come from GKG enrichment later
                seendate = art.get("seendate", "")
                language = art.get("language", "")
                socialimage = art.get("socialimage", "")

                cursor.execute(sql, (
                    query_id,
                    run_date,
                    url[:2048],
                    domain[:255],
                    title,
                    "",  # snippet — filled by processor
                    "",  # gdelt_themes — filled by GKG enrichment
                    tone if tone else None,
                    None,  # gdelt_entities
                    None,  # gdelt_locations
                    pir_id,
                    sir_id,
                    json.dumps({
                        "seendate": seendate,
                        "language": language,
                        "socialimage": socialimage,
                        "source_query": query_text,
                    }),
                ))
                stored += 1
            except Exception as e:
                logger.debug(f"Article store error: {e}")
                continue

    return stored


def _store_gkg_records(records: list[dict], run_date: str) -> int:
    """Store filtered GKG records into raw_collection."""
    if not records:
        return 0

    sql = """
        INSERT INTO raw_collection
            (collection_date, source_url, source_name, title,
             gdelt_themes, gdelt_tone, gdelt_entities, gdelt_locations,
             raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE gdelt_tone = VALUES(gdelt_tone)
    """

    stored = 0
    with get_cursor() as cursor:
        for record in records:
            try:
                url = record.get("url", "")
                if not url:
                    continue

                themes_str = ";".join(record.get("themes", []))
                persons = record.get("persons", [])
                orgs = record.get("organizations", [])
                locations = record.get("locations", [])

                entities_json = json.dumps({
                    "persons": persons[:20],  # Cap for storage
                    "organizations": orgs[:20],
                })
                locations_json = json.dumps(locations[:20])

                cursor.execute(sql, (
                    run_date,
                    url[:2048],
                    record.get("source", "")[:255],
                    "",  # Title not in GKG
                    themes_str[:2000],
                    record.get("tone"),
                    entities_json,
                    locations_json,
                    json.dumps({"gkg_id": record.get("gkg_id"), "word_count": record.get("word_count")}),
                ))
                stored += 1
            except Exception as e:
                logger.debug(f"GKG store error: {e}")
                continue

    return stored


def _get_query_id(query_text: str, pir_id: str, sir_id: str) -> Optional[int]:
    """Look up query_id from collection_plan. Returns None if not found."""
    try:
        rows = execute_query(
            "SELECT query_id FROM collection_plan WHERE pir_id = %s AND sir_id = %s LIMIT 1",
            (pir_id, sir_id),
        )
        if rows:
            return rows[0]["query_id"]
    except Exception:
        pass
    return None


def _update_query_yield(query_id: int, article_count: int):
    """Update the collection_plan yield metrics after a query run."""
    if query_id is None:
        return
    try:
        with get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE collection_plan
                SET last_run = NOW(),
                    last_yield = %s,
                    total_runs = total_runs + 1,
                    total_results = total_results + %s,
                    low_yield_days = CASE WHEN %s = 0 THEN low_yield_days + 1 ELSE 0 END
                WHERE query_id = %s
                """,
                (article_count, article_count, article_count, query_id),
            )
    except Exception as e:
        logger.debug(f"Yield update error: {e}")
