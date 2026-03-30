"""
SENTINEL2 — Geophysical Metric Collectors
Metrics: #2 NASA FIRMS Thermal Anomalies, #21 Seismic Activity, #28 IAEA Reports
"""

import os
import logging
import requests

logger = logging.getLogger("sentinel2.metrics.geophysical")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}

# ME/Caucasus bounding box
_ME_BBOX = {"west": 25.0, "south": 12.0, "east": 65.0, "north": 45.0}


def collect_firms_hotspots(run_date: str) -> dict:
    """Metric #2: NASA FIRMS fire/thermal anomalies in ME/Caucasus."""
    api_key = os.environ.get("NASA_FIRMS_API_KEY", "")
    if not api_key:
        return {"value": None, "raw_json": {}, "notes": "NASA_FIRMS_API_KEY not set"}

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{api_key}/VIIRS_SNPP_NRT/"
        f"{_ME_BBOX['west']},{_ME_BBOX['south']},{_ME_BBOX['east']},{_ME_BBOX['north']}/1"
    )
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        count = max(0, len(lines) - 1)  # Subtract header
        return {
            "value": float(count),
            "raw_json": {"hotspot_count": count, "source": "VIIRS_SNPP_NRT"},
            "notes": f"FIRMS: {count} thermal anomalies in ME/Caucasus",
        }
    except Exception as e:
        logger.warning(f"NASA FIRMS failed: {e}")
        return {"value": None, "raw_json": {"error": str(e)}, "notes": f"FIRMS error: {e}"}


def collect_seismic(run_date: str) -> dict:
    """Metric #21: Seismic activity along Anatolian/Caucasus fault zones."""
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?"
        f"format=geojson&starttime={run_date}&endtime={run_date}"
        f"&minlatitude={_ME_BBOX['south']}&maxlatitude={_ME_BBOX['north']}"
        f"&minlongitude={_ME_BBOX['west']}&maxlongitude={_ME_BBOX['east']}"
        "&minmagnitude=3.0"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        count = len(features)
        max_mag = max((f["properties"]["mag"] for f in features), default=0)
        return {
            "value": float(count),
            "raw_json": {"earthquake_count": count, "max_magnitude": max_mag},
            "notes": f"Seismic: {count} events ≥M3.0, max M{max_mag}",
        }
    except Exception as e:
        logger.warning(f"USGS seismic failed: {e}")
        return {"value": None, "raw_json": {"error": str(e)}, "notes": f"USGS error: {e}"}


def collect_iaea_reports(run_date: str) -> dict:
    """Metric #28: IAEA inspection activity/reports on Iran."""
    try:
        import feedparser
        feed = feedparser.parse("https://www.iaea.org/feeds/press-releases")
        iran_entries = [
            e for e in feed.entries
            if any(kw in e.get("title", "").lower() for kw in ["iran", "jcpoa", "enrichment", "safeguards"])
        ]
        return {
            "value": float(len(iran_entries)),
            "raw_json": {"iran_mentions": len(iran_entries),
                         "titles": [e.get("title", "") for e in iran_entries[:5]]},
            "notes": f"IAEA: {len(iran_entries)} Iran-related releases",
        }
    except Exception as e:
        logger.warning(f"IAEA feed failed: {e}")
        return {"value": None, "raw_json": {"error": str(e)}, "notes": f"IAEA error: {e}"}
