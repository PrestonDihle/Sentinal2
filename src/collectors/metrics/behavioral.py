"""
SENTINEL2 — Behavioral Metric Collectors
Metrics: #8 Social Media Sentiment (GDELT), #19 Telegram Activity,
         #25 YouTube Propaganda Volume
"""

import os
import logging
import time

import requests

logger = logging.getLogger("sentinel2.metrics.behavioral")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
_ME_COUNTRIES = ["Iran", "Israel", "Syria", "Yemen", "Lebanon", "Iraq", "Turkey", "Saudi Arabia"]


def collect_gdelt_sentiment(run_date: str) -> dict:
    """Metric #8: GDELT social media sentiment for ME region."""
    scores = []
    country_tones = {}

    for country in _ME_COUNTRIES:
        try:
            resp = requests.get(_GDELT_DOC, params={
                "query": country,
                "mode": "timelinetone",
                "timespan": "1d",
                "format": "json",
            }, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            timeline = data.get("timeline", [])
            if timeline and isinstance(timeline[0], dict):
                series = timeline[0].get("data", [])
                if series:
                    values = [float(p.get("value", 0)) for p in series if "value" in p]
                    if values:
                        avg = sum(values) / len(values)
                        country_tones[country] = round(avg, 3)
                        scores.append(avg)
        except Exception as e:
            logger.debug(f"GDELT tone {country}: {e}")
        time.sleep(1)

    overall = round(sum(scores) / len(scores), 3) if scores else None
    return {
        "value": overall,
        "raw_json": {"country_tones": country_tones, "overall_avg": overall},
        "notes": f"GDELT sentiment: {overall} ({len(scores)} countries)",
    }


def collect_telegram_activity(run_date: str) -> dict:
    """Metric #19: Telegram channel activity volume."""
    # Telegram monitoring requires channel scraping or API access
    # Placeholder — implement with Telethon or tg-archive when authorized
    return {
        "value": None,
        "raw_json": {"status": "not_configured"},
        "notes": "Telegram monitoring requires Telethon setup — placeholder",
    }


def collect_youtube_propaganda(run_date: str) -> dict:
    """Metric #25: YouTube propaganda volume from ME region."""
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"value": None, "raw_json": {}, "notes": "YOUTUBE_API_KEY not set"}

    keywords = [
        "military operation Middle East",
        "militia attack video",
        "Houthi missile launch",
        "resistance operation video",
    ]
    total = 0
    keyword_data = {}

    for kw in keywords:
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": api_key,
                    "part": "snippet",
                    "q": kw,
                    "type": "video",
                    "publishedAfter": f"{run_date}T00:00:00Z",
                    "maxResults": 50,
                    "relevanceLanguage": "ar",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("pageInfo", {}).get("totalResults", 0)
                keyword_data[kw] = count
                total += min(count, 1000)  # Cap to avoid outliers
        except Exception as e:
            logger.debug(f"YouTube {kw}: {e}")

    return {
        "value": float(total),
        "raw_json": {"keywords": keyword_data, "total": total},
        "notes": f"YouTube propaganda: {total} estimated videos",
    }
