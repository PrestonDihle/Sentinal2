"""
SENTINEL2 — GDELT GEO 2.0 API Tool (CrewAI BaseTool)
Retrieves geographic point data and heatmaps in GeoJSON format.

API endpoint: https://api.gdeltproject.org/api/v2/geo/geo
7-day rolling window, up to 25,000 points per query.
No authentication required.
"""

import json
import time
import logging
from typing import Optional

import requests
from crewai.tools import BaseTool

logger = logging.getLogger("sentinel2.tools.gdelt_geo")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_BASE_URL = "https://api.gdeltproject.org/api/v2/geo/geo"

# Bounding box for Greater Middle East + Caucasus region
# (approximate: 10°N to 50°N, 20°E to 65°E)
_ME_CAUCASUS_BBOX = {
    "south": 10.0,
    "north": 50.0,
    "west": 20.0,
    "east": 65.0,
}


class GDELTGeoTool(BaseTool):
    """Query GDELT GEO 2.0 API for geographic activity data."""

    name: str = "gdelt_geo_search"
    description: str = (
        "Query the GDELT GEO 2.0 API for geographic point data in GeoJSON. "
        "Returns locations of news events with 7-day rolling window. "
        "Input: JSON with 'query' (search terms), 'mode' (pointdata|heatmap), "
        "'timespan' (e.g., '1d', '7d')."
    )

    def _run(self, input_str: str) -> str:
        try:
            params = json.loads(input_str) if isinstance(input_str, str) else input_str
        except json.JSONDecodeError:
            params = {"query": input_str}

        query = params.get("query", "Middle East conflict")
        mode = params.get("mode", "pointdata")
        timespan = params.get("timespan", "1d")

        result = gdelt_geo_query(query=query, mode=mode, timespan=timespan)
        return json.dumps(result)


def gdelt_geo_query(
    query: str,
    mode: str = "pointdata",
    timespan: str = "1d",
    maxpoints: int = 5000,
    format: str = "geojson",
    sourcecountry: Optional[str] = None,
) -> dict:
    """
    Query GDELT GEO 2.0 API.

    Args:
        query: Search terms
        mode: pointdata | heatmap
        timespan: Time window (e.g., '1d', '7d')
        maxpoints: Max points to return (up to 25000)
        format: geojson | csv
        sourcecountry: FIPS code filter

    Returns:
        GeoJSON dict with features, or error dict.
    """
    full_query = query
    if sourcecountry:
        full_query += f" sourcecountry:{sourcecountry}"

    params = {
        "query": full_query,
        "mode": mode,
        "maxpoints": maxpoints,
        "timespan": timespan,
        "format": format,
    }

    try:
        time.sleep(1)  # Rate limit
        resp = requests.get(_BASE_URL, params=params, headers=_HEADERS, timeout=30)
        resp.raise_for_status()

        if format == "geojson":
            data = resp.json()
            features = data.get("features", [])
            logger.info(f"GDELT GEO: '{query}' → {len(features)} points")

            # Filter to ME/Caucasus bounding box
            filtered_features = []
            for feature in features:
                coords = feature.get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    if (_ME_CAUCASUS_BBOX["south"] <= lat <= _ME_CAUCASUS_BBOX["north"] and
                            _ME_CAUCASUS_BBOX["west"] <= lon <= _ME_CAUCASUS_BBOX["east"]):
                        filtered_features.append(feature)

            return {
                "type": "FeatureCollection",
                "query": query,
                "total_points": len(features),
                "filtered_points": len(filtered_features),
                "features": filtered_features,
            }
        else:
            return {"raw": resp.text}

    except Exception as e:
        logger.error(f"GDELT GEO error: {e}")
        return {"error": str(e), "query": query}


def get_daily_heatmap(date_str: Optional[str] = None) -> dict:
    """
    Generate a daily activity heatmap for the ME/Caucasus region.
    Queries multiple conflict-related terms and merges results.
    """
    queries = [
        "conflict military Middle East",
        "protest demonstration Caucasus",
        "terrorism attack bombing",
        "missile drone strike",
        "border tension escalation",
    ]

    all_features = []
    for q in queries:
        result = gdelt_geo_query(query=q, mode="pointdata", timespan="1d", maxpoints=2000)
        if "features" in result:
            all_features.extend(result["features"])

    # Deduplicate by coordinates (rounded to 2 decimal places)
    seen = set()
    unique_features = []
    for f in all_features:
        coords = f.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            key = (round(coords[0], 2), round(coords[1], 2))
            if key not in seen:
                seen.add(key)
                unique_features.append(f)

    logger.info(f"Daily heatmap: {len(unique_features)} unique points")
    return {
        "type": "FeatureCollection",
        "date": date_str,
        "total_unique_points": len(unique_features),
        "features": unique_features,
    }
