"""
SENTINEL2 — Web Search Tool
CrewAI tool wrapping DuckDuckGo search for supplementary web queries.
Also includes a Google News search function.
"""

import logging
from typing import Optional

from crewai.tools import BaseTool

logger = logging.getLogger("sentinel2.tools.web_search")


class WebSearchTool(BaseTool):
    name: str = "Web Search Tool"
    description: str = (
        "Search the web using DuckDuckGo for supplementary intelligence collection. "
        "Returns top results with titles, snippets, and URLs. "
        "Use for queries that GDELT may not cover well (niche sources, forums, etc.)."
    )

    def _run(self, query: str, max_results: int = 10) -> str:
        results = duckduckgo_search(query, max_results=max_results)
        if not results:
            return f"No results found for: {query}"
        lines = []
        for r in results:
            lines.append(
                f"- {r.get('title', 'N/A')}\n"
                f"  {r.get('snippet', '')}\n"
                f"  URL: {r.get('url', '')}"
            )
        return f"Results for '{query}':\n" + "\n".join(lines)


class GoogleNewsTool(BaseTool):
    name: str = "Google News Search Tool"
    description: str = (
        "Search Google News for recent news articles on a topic. "
        "Returns top headlines with titles, snippets, and URLs."
    )

    def _run(self, query: str, max_results: int = 10) -> str:
        results = google_news_search(query, max_results=max_results)
        if not results:
            return f"No Google News results for: {query}"
        lines = []
        for r in results:
            lines.append(
                f"- {r.get('title', 'N/A')}\n"
                f"  {r.get('snippet', '')}\n"
                f"  URL: {r.get('url', '')}"
            )
        return f"Google News results for '{query}':\n" + "\n".join(lines)


def duckduckgo_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Search DuckDuckGo and return results.

    Returns list of dicts with: title, snippet, url.
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []


def google_news_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Search Google News via DuckDuckGo news endpoint.

    Returns list of dicts with: title, snippet, url, date.
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("url", ""),
                    "date": r.get("date", ""),
                })
        return results
    except Exception as e:
        logger.warning(f"Google News search failed: {e}")
        return []
