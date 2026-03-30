"""
SENTINEL2 — Web Scrape Tool
CrewAI tool for scraping full article text from URLs.
Used by CMA when a critical story needs full text extraction.
"""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool

logger = logging.getLogger("sentinel2.tools.web_scrape")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0; +research)"
}
_TIMEOUT = 20
_MAX_TEXT_LENGTH = 15000


class WebScrapeTool(BaseTool):
    name: str = "Web Scrape Tool"
    description: str = (
        "Scrape the full text content of a web page given its URL. "
        "Returns the article text, title, and metadata. "
        "Use this when you need the full article text beyond what GDELT provides."
    )

    def _run(self, url: str) -> str:
        result = web_scrape(url)
        if result.get("error"):
            return f"Error scraping {url}: {result['error']}"
        return (
            f"Title: {result.get('title', 'N/A')}\n"
            f"Text ({result.get('text_length', 0)} chars):\n"
            f"{result.get('text', '')}"
        )


def web_scrape(url: str) -> dict:
    """
    Scrape a URL and extract the main article text.

    Returns dict with: title, text, text_length, url, error.
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        # Remove script/style/nav elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Try article tag first, then main, then body
        article = soup.find("article") or soup.find("main") or soup.body
        if article is None:
            article = soup

        # Extract text
        text = article.get_text(separator="\n", strip=True)

        # Truncate if too long
        if len(text) > _MAX_TEXT_LENGTH:
            text = text[:_MAX_TEXT_LENGTH] + "\n[TRUNCATED]"

        return {
            "title": title,
            "text": text,
            "text_length": len(text),
            "url": url,
        }

    except requests.RequestException as e:
        logger.debug(f"Scrape failed for {url}: {e}")
        return {"url": url, "error": str(e)}
    except Exception as e:
        logger.debug(f"Parse failed for {url}: {e}")
        return {"url": url, "error": str(e)}
