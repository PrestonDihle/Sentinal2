"""
SENTINEL2 — RSS Feed Tool
CrewAI tool for monitoring RSS feeds (Reuters, CENTCOM, Al Jazeera, etc.).
"""

import logging
from typing import Optional
from datetime import datetime

import feedparser
from crewai.tools import BaseTool

logger = logging.getLogger("sentinel2.tools.rss_feed")

# Default feeds for Middle East intelligence monitoring
DEFAULT_FEEDS = {
    "reuters_me": "https://www.reutersagency.com/feed/?taxonomy=best-regions&post_tag=middle-east",
    "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "bbc_me": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "centcom": "https://www.centcom.mil/MEDIA/PRESS-RELEASES/Press-Release-View/rssfeed/",
    "reliefweb": "https://reliefweb.int/updates/rss.xml",
    "iaea": "https://www.iaea.org/feeds/press-releases",
    "un_news": "https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml",
    "crisis_group": "https://www.crisisgroup.org/feed/rss",
}


class RSSFeedTool(BaseTool):
    name: str = "RSS Feed Monitor"
    description: str = (
        "Monitor RSS feeds for recent articles. Can query specific feed URLs "
        "or use built-in feeds: reuters_me, aljazeera, bbc_me, centcom, "
        "reliefweb, iaea, un_news, crisis_group. "
        "Pass a feed name or URL as the query parameter."
    )

    def _run(self, query: str, max_items: int = 15) -> str:
        # Check if query is a known feed name
        url = DEFAULT_FEEDS.get(query.lower(), query)
        items = fetch_rss(url, max_items=max_items)
        if not items:
            return f"No items from feed: {query}"
        lines = [f"RSS Feed: {query} ({len(items)} items)"]
        for item in items:
            lines.append(
                f"- [{item.get('published', 'N/A')}] {item.get('title', 'N/A')}\n"
                f"  {item.get('summary', '')[:200]}\n"
                f"  URL: {item.get('url', '')}"
            )
        return "\n".join(lines)


def fetch_rss(url: str, max_items: int = 15) -> list[dict]:
    """
    Fetch and parse an RSS feed.

    Returns list of dicts with: title, summary, url, published.
    """
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            elif hasattr(entry, "updated"):
                published = entry.updated

            items.append({
                "title": getattr(entry, "title", ""),
                "summary": getattr(entry, "summary", ""),
                "url": getattr(entry, "link", ""),
                "published": published,
            })
        return items
    except Exception as e:
        logger.warning(f"RSS fetch failed for {url}: {e}")
        return []


def fetch_all_default_feeds(max_per_feed: int = 10) -> dict[str, list[dict]]:
    """Fetch all default feeds. Returns dict of feed_name → items."""
    results = {}
    for name, url in DEFAULT_FEEDS.items():
        items = fetch_rss(url, max_items=max_per_feed)
        results[name] = items
        logger.debug(f"RSS {name}: {len(items)} items")
    return results
