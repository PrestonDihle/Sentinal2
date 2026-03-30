"""
SENTINEL2 — GDELT DOC 2.0 API Tool (CrewAI BaseTool)
Wraps the GDELT DOC 2.0 API for fulltext news search.

API Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
Endpoint: https://api.gdeltproject.org/api/v2/doc/doc

Modes:
  - artlist: Returns article list with title, URL, tone, source, date
  - timelinetone: Returns tone timeline data
  - timelinevol: Returns volume timeline data

No authentication required. Rolling 3-month window.
"""

import time
import json
import logging
from typing import Optional

import requests
from crewai.tools import BaseTool

from src.utils.config import get_config

logger = logging.getLogger("sentinel2.tools.gdelt_doc")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTDocSearchTool(BaseTool):
    """Search GDELT DOC 2.0 API for news articles matching a query."""

    name: str = "gdelt_doc_search"
    description: str = (
        "Search the GDELT DOC 2.0 API for global news articles. "
        "Supports fulltext search across 65 languages with pre-tagged tone, "
        "themes, source country, and entities. "
        "Input should be a JSON string with keys: "
        "'query' (required), 'mode' (artlist|timelinetone|timelinevol), "
        "'timespan' (e.g. '1d', '7d'), 'maxrecords' (int), "
        "'sourcecountry' (FIPS code), 'theme' (GDELT theme)."
    )

    def _run(self, input_str: str) -> str:
        """Execute GDELT DOC 2.0 search."""
        try:
            params = json.loads(input_str) if isinstance(input_str, str) else input_str
        except json.JSONDecodeError:
            params = {"query": input_str}

        return gdelt_doc_search(**params)


def gdelt_doc_search(
    query: str,
    mode: str = "artlist",
    timespan: str = "1d",
    maxrecords: int = 250,
    sourcecountry: Optional[str] = None,
    theme: Optional[str] = None,
    format: str = "json",
    sort: str = "hybridrel",
) -> str:
    """
    Query the GDELT DOC 2.0 API directly.

    Args:
        query: Fulltext search query (supports GDELT query syntax:
               near10, theme:, sourcecountry:, etc.)
        mode: artlist | timelinetone | timelinevol
        timespan: Time window (e.g., '1d', '7d', '3m')
        maxrecords: Max articles returned (up to 250)
        sourcecountry: FIPS country code filter
        theme: GDELT theme code filter
        format: json | csv
        sort: hybridrel | date | toneasc | tonedesc

    Returns:
        JSON string with articles or timeline data.
    """
    # Build the full query string with optional filters
    full_query = query
    if sourcecountry:
        full_query += f" sourcecountry:{sourcecountry}"
    if theme:
        full_query += f" theme:{theme}"

    params = {
        "query": full_query,
        "mode": mode,
        "maxrecords": maxrecords,
        "timespan": timespan,
        "format": format,
        "sort": sort,
    }

    config = get_config()
    delay = config.get("gdelt", {}).get("request_delay_seconds", 1.0)

    try:
        time.sleep(delay)
        resp = requests.get(_BASE_URL, params=params, headers=_HEADERS, timeout=30)
        resp.raise_for_status()

        if format == "json":
            data = resp.json()
            if mode == "artlist":
                articles = data.get("articles", [])
                logger.info(f"GDELT DOC: '{query}' → {len(articles)} articles")
                return json.dumps({
                    "query": query,
                    "mode": mode,
                    "article_count": len(articles),
                    "articles": articles,
                })
            else:
                # Timeline modes
                return json.dumps(data)
        else:
            return resp.text

    except requests.exceptions.HTTPError as e:
        if resp.status_code == 429:
            logger.warning("GDELT rate limited, backing off 10s")
            time.sleep(10)
            return json.dumps({"error": "rate_limited", "query": query})
        logger.error(f"GDELT DOC error: {e}")
        return json.dumps({"error": str(e), "query": query})
    except Exception as e:
        logger.error(f"GDELT DOC error: {e}")
        return json.dumps({"error": str(e), "query": query})


def gdelt_doc_artlist(
    query: str,
    timespan: str = "1d",
    maxrecords: int = 250,
    sourcecountry: Optional[str] = None,
    theme: Optional[str] = None,
) -> list[dict]:
    """
    Convenience function: returns parsed article list directly.

    Returns list of dicts with keys:
        url, title, seendate, socialimage, domain, language,
        sourcecountry, tone
    """
    raw = gdelt_doc_search(
        query=query,
        mode="artlist",
        timespan=timespan,
        maxrecords=maxrecords,
        sourcecountry=sourcecountry,
        theme=theme,
    )
    try:
        data = json.loads(raw)
        return data.get("articles", [])
    except json.JSONDecodeError:
        return []


def gdelt_doc_tone(
    query: str,
    timespan: str = "7d",
    sourcecountry: Optional[str] = None,
) -> list[dict]:
    """
    Convenience function: returns tone timeline data.

    Returns list of dicts with keys: date, value (tone score).
    """
    raw = gdelt_doc_search(
        query=query,
        mode="timelinetone",
        timespan=timespan,
        sourcecountry=sourcecountry,
    )
    try:
        data = json.loads(raw)
        timeline = data.get("timeline", [])
        if timeline and isinstance(timeline[0], dict):
            return timeline[0].get("data", [])
        return []
    except json.JSONDecodeError:
        return []


def gdelt_doc_volume(
    query: str,
    timespan: str = "7d",
    sourcecountry: Optional[str] = None,
) -> list[dict]:
    """
    Convenience function: returns volume timeline data.
    """
    raw = gdelt_doc_search(
        query=query,
        mode="timelinevol",
        timespan=timespan,
        sourcecountry=sourcecountry,
    )
    try:
        data = json.loads(raw)
        timeline = data.get("timeline", [])
        if timeline and isinstance(timeline[0], dict):
            return timeline[0].get("data", [])
        return []
    except json.JSONDecodeError:
        return []
