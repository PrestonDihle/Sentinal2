"""
SENTINEL2 — Lean LLM Processor
Uses Gemini Flash for PIR/SIR mapping, significance judgment, and snippet
generation. GDELT already provides themes, entities, tone, and countries,
so this processor only handles what GDELT can't:
    - Human-readable snippet summarization
    - Significance assessment (LOW/MED/HIGH)
    - Confidence assignment (Low/Moderate/High)
    - Country and topic tagging refinement
    - Duplicate merging across sources

~70% fewer LLM calls than Sentinel v1.
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Optional

from src.utils.llm import call_llm, call_llm_json
from src.utils.config import get_config, get_project_root
from src.db.connection import get_cursor, execute_query

logger = logging.getLogger("sentinel2.agents.processor")

# System prompt for the lean processor
_PROCESSOR_SYSTEM = """You are an all-source intelligence analyst in the SENTINEL2 pipeline.
Your task is to process raw news articles into structured intelligence items.

For each batch of articles (same SIR), produce a JSON array of processed items.
Each item must have:
- "title": Concise analytical title (max 80 chars)
- "summary": 2-3 sentence analytical summary (evidence-based, no speculation)
- "significance": "LOW", "MED", or "HIGH"
- "confidence": "Low", "Moderate", or "High" (ICD 203 language)
- "country": Primary country involved
- "topic": Primary topic tag
- "is_duplicate": true if this is substantially the same event as another item

Significance criteria:
- HIGH: Direct threat indicators, confirmed military action, treaty violations, mass casualty events
- MED: Escalatory rhetoric, troop/weapon movements, economic disruptions, diplomatic shifts
- LOW: Routine coverage, background context, minor incidents

Use ICD 203 confidence language:
- Low: Fragmentary information, multiple interpretations, single unverified source
- Moderate: Multiple consistent sources, plausible but not confirmed
- High: Confirmed by multiple independent sources with direct evidence

Be concise. Ground every assessment in the evidence provided. Do not speculate."""


def run_processor(
    run_date: Optional[str] = None,
    batch_size: int = 500,
    max_workers: int = 4,
) -> dict:
    """
    Process raw_collection items into processed_collection items.

    Groups raw items by SIR, then processes batches in parallel through
    Gemini Flash for significance assessment and snippet generation.

    Args:
        run_date: ISO date string (default: today)
        batch_size: Number of raw items per LLM call (500 ≈ half Flash context)
        max_workers: Parallel processing threads (4 stays within Gemini 15 RPM)

    Returns:
        Summary dict with processing stats.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    stats = {
        "run_date": run_date,
        "raw_items_processed": 0,
        "processed_items_created": 0,
        "high_count": 0,
        "med_count": 0,
        "low_count": 0,
        "errors": [],
    }

    # Fetch unprocessed raw items for today
    raw_items = _fetch_raw_items(run_date)
    if not raw_items:
        logger.info(f"No raw items to process for {run_date}")
        return stats

    logger.info(f"Processing {len(raw_items)} raw items for {run_date}")

    # Group by PIR/SIR
    sir_groups = {}
    for item in raw_items:
        key = item.get("sir_id") or item.get("pir_id") or "untagged"
        if key not in sir_groups:
            sir_groups[key] = []
        sir_groups[key].append(item)

    # Build all batch jobs
    batch_jobs = []
    for sir_id, items in sir_groups.items():
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_jobs.append((batch, sir_id, run_date))

    logger.info(
        f"Processing {len(raw_items)} items in {len(batch_jobs)} batches "
        f"across {max_workers} parallel workers"
    )

    # Process batches in parallel using ThreadPoolExecutor
    # Gemini Flash rate limit: 15 RPM → 4 workers keeps us within limits
    stats_lock = threading.Lock()

    def _process_and_collect(job):
        batch, sir_id, rd = job
        try:
            processed = _process_batch(batch, sir_id, rd)
            return batch, sir_id, processed, None
        except Exception as e:
            return batch, sir_id, [], e

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_and_collect, job): job for job in batch_jobs}
        for future in as_completed(futures):
            batch, sir_id, processed, error = future.result()
            with stats_lock:
                if error:
                    logger.warning(f"Batch processing error (SIR {sir_id}): {error}")
                    stats["errors"].append({"sir_id": sir_id, "error": str(error)})
                else:
                    stats["raw_items_processed"] += len(batch)
                    stats["processed_items_created"] += len(processed)
                    for p in processed:
                        sig = p.get("significance", "MED")
                        if sig == "HIGH":
                            stats["high_count"] += 1
                        elif sig == "LOW":
                            stats["low_count"] += 1
                        else:
                            stats["med_count"] += 1

    logger.info(
        f"Processing complete: {stats['processed_items_created']} items "
        f"(H:{stats['high_count']} M:{stats['med_count']} L:{stats['low_count']})"
    )
    return stats


def _fetch_raw_items(run_date: str) -> list[dict]:
    """Fetch raw_collection items for the given date that haven't been processed."""
    sql = """
        SELECT rc.item_id, rc.title, rc.source_url, rc.source_name,
               rc.snippet, rc.gdelt_themes, rc.gdelt_tone,
               rc.gdelt_entities, rc.gdelt_locations,
               rc.pir_id, rc.sir_id, rc.raw_json
        FROM raw_collection rc
        WHERE rc.collection_date = %s
          AND rc.is_duplicate = FALSE
        ORDER BY rc.pir_id, rc.sir_id
    """
    return execute_query(sql, (run_date,))


def _process_batch(
    batch: list[dict],
    sir_id: str,
    run_date: str,
) -> list[dict]:
    """
    Process a batch of raw items through Gemini Flash.
    Returns list of processed items stored in the database.
    """
    # Build the prompt with article data
    articles_text = []
    item_ids = []
    for item in batch:
        item_ids.append(item["item_id"])
        title = item.get("title") or ""
        source = item.get("source_name") or ""
        url = item.get("source_url") or ""
        themes = item.get("gdelt_themes") or ""
        tone = item.get("gdelt_tone")

        articles_text.append(
            f"[{item['item_id']}] {title}\n"
            f"  Source: {source} | URL: {url}\n"
            f"  GDELT Themes: {themes}\n"
            f"  GDELT Tone: {tone}"
        )

    pir_id = batch[0].get("pir_id") or "unknown"
    prompt = (
        f"SIR: {sir_id} | PIR: {pir_id} | Date: {run_date}\n\n"
        f"Process the following {len(batch)} articles into structured intelligence items.\n"
        f"Merge duplicates (same event from different sources) into single items.\n"
        f"Return a JSON array of processed items.\n\n"
        f"Articles:\n" + "\n\n".join(articles_text)
    )

    # Call Gemini Flash (lean processor)
    result = call_llm_json(
        prompt=prompt,
        system_prompt=_PROCESSOR_SYSTEM,
        component="processor",
    )

    # Handle response
    if isinstance(result, dict) and "error" in result:
        logger.warning(f"Processor LLM error: {result['error']}")
        return []

    if not isinstance(result, list):
        result = [result] if isinstance(result, dict) else []

    # Store processed items
    stored = []
    for processed_item in result:
        try:
            _store_processed_item(processed_item, sir_id, pir_id, run_date, item_ids)
            stored.append(processed_item)
        except Exception as e:
            logger.debug(f"Store error: {e}")

    return stored


def _store_processed_item(
    item: dict,
    sir_id: str,
    pir_id: str,
    run_date: str,
    source_item_ids: list[int],
):
    """Store a single processed item into processed_collection."""
    sql = """
        INSERT INTO processed_collection
            (run_date, title, summary, source_urls, pir_id, indicator_id,
             sir_id, country, topic, significance, confidence,
             is_duplicate_merge, merged_count, source_item_ids)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Extract indicator_id from sir_id (e.g., SIR1.1.1 → 1.1)
    parts = sir_id.replace("SIR", "").split(".")
    indicator_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else sir_id

    is_dup = item.get("is_duplicate", False)
    merged_count = item.get("merged_count", 1)

    with get_cursor() as cursor:
        cursor.execute(sql, (
            run_date,
            (item.get("title") or "")[:512],
            item.get("summary", ""),
            "",  # source_urls — could be filled from raw items
            pir_id,
            indicator_id,
            sir_id,
            item.get("country", ""),
            item.get("topic", ""),
            item.get("significance", "MED"),
            item.get("confidence", "Moderate"),
            is_dup,
            merged_count,
            json.dumps(source_item_ids),
        ))
