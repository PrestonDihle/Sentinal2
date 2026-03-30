"""
SENTINEL2 — Telegram Monitor Tool
CrewAI tool for monitoring public Telegram channels.
Uses web-based scraping of t.me/s/ (public preview) as a fallback
when the Telegram API is not configured.
"""

import logging
import os
from typing import Optional

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool

logger = logging.getLogger("sentinel2.tools.telegram")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0; +research)"
}

# Default channels for Middle East monitoring
DEFAULT_CHANNELS = [
    "middleeasteye",
    "iranintl",
    "alaborignews",
    "SyrianObservatory",
]


class TelegramMonitorTool(BaseTool):
    name: str = "Telegram Channel Monitor"
    description: str = (
        "Monitor public Telegram channels for recent posts. "
        "Pass a channel username (without @) to fetch recent messages. "
        "Only works with channels that have public web previews enabled."
    )

    def _run(self, channel: str, max_posts: int = 10) -> str:
        posts = fetch_telegram_channel(channel, max_posts=max_posts)
        if not posts:
            return f"No posts retrieved from Telegram channel: {channel}"
        lines = [f"Telegram @{channel} ({len(posts)} posts):"]
        for p in posts:
            lines.append(
                f"- [{p.get('datetime', 'N/A')}] {p.get('text', '')[:300]}"
            )
        return "\n".join(lines)


def fetch_telegram_channel(
    channel: str, max_posts: int = 10
) -> list[dict]:
    """
    Fetch recent posts from a public Telegram channel via web preview.

    Returns list of dicts with: text, datetime, views, url.
    """
    url = f"https://t.me/s/{channel}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        messages = soup.find_all(
            "div", class_="tgme_widget_message_wrap"
        )

        posts = []
        for msg in messages[-max_posts:]:
            text_div = msg.find("div", class_="tgme_widget_message_text")
            text = text_div.get_text(strip=True) if text_div else ""

            time_tag = msg.find("time")
            dt = time_tag.get("datetime", "") if time_tag else ""

            views_span = msg.find("span", class_="tgme_widget_message_views")
            views = views_span.get_text(strip=True) if views_span else ""

            msg_link = msg.find("a", class_="tgme_widget_message_date")
            post_url = msg_link.get("href", "") if msg_link else ""

            posts.append({
                "text": text,
                "datetime": dt,
                "views": views,
                "url": post_url,
            })

        return posts

    except Exception as e:
        logger.debug(f"Telegram channel {channel} fetch failed: {e}")
        return []


def fetch_default_channels(max_per_channel: int = 5) -> dict[str, list[dict]]:
    """Fetch all default monitored channels."""
    results = {}
    for ch in DEFAULT_CHANNELS:
        posts = fetch_telegram_channel(ch, max_posts=max_per_channel)
        results[ch] = posts
        logger.debug(f"Telegram @{ch}: {len(posts)} posts")
    return results
