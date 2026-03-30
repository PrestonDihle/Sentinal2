"""
SENTINEL2 — Conflict Metric Collectors
Metrics: #4 GDELT Conflict Events, #29 ACLED Protest Events
"""

import io
import csv
import logging
import os
import time
import zipfile

import requests

logger = logging.getLogger("sentinel2.metrics.conflict")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_GDELT_ME_FIPS = {"IR", "IZ", "SY", "LE", "YM", "IS", "WE", "TU", "SA", "AE", "JO", "EG"}
_CONFLICT_CAMEO = {"18", "19", "20"}  # Assault, Fight, Unconventional mass violence


def collect_gdelt_events(run_date: str) -> dict:
    """Metric #4: GDELT 2.0 conflict events in monitored countries."""
    date_compact = run_date.replace("-", "")
    hours = range(24)
    minutes = ["0000", "1500", "3000", "4500"]
    urls = [
        f"http://data.gdeltproject.org/gdeltv2/{date_compact}{h:02d}{m}.export.CSV.zip"
        for h in hours for m in minutes
    ]

    country_counts = {}
    total = 0
    files_ok = 0

    for url in urls[:48]:  # First 12 hours to avoid timeouts
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            files_ok += 1

            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                fname = zf.namelist()[0]
                with zf.open(fname) as f:
                    reader = csv.reader(
                        io.TextIOWrapper(f, encoding="utf-8", errors="replace"),
                        delimiter="\t",
                    )
                    for row in reader:
                        if len(row) < 58:
                            continue
                        cameo_root = row[26][:2] if len(row[26]) >= 2 else ""
                        actor1_cc = row[7] if len(row) > 7 else ""
                        actor2_cc = row[17] if len(row) > 17 else ""

                        if cameo_root in _CONFLICT_CAMEO:
                            for cc in [actor1_cc, actor2_cc]:
                                if cc in _GDELT_ME_FIPS:
                                    country_counts[cc] = country_counts.get(cc, 0) + 1
                                    total += 1
                                    break
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"GDELT event file error: {e}")

    return {
        "value": float(total),
        "raw_json": {"country_counts": country_counts, "files_processed": files_ok},
        "notes": f"GDELT conflict events: {total} across {len(country_counts)} countries",
    }


def collect_acled_protests(run_date: str) -> dict:
    """Metric #29: ACLED protest/civil unrest events in ME."""
    api_key = os.environ.get("ACLED_API_KEY", "")
    email = os.environ.get("ACLED_EMAIL", "")

    if not api_key or not email:
        # Fallback to GDELT protest approximation
        return _gdelt_protest_fallback(run_date)

    acled_countries = ["Iran", "Iraq", "Syria", "Lebanon", "Yemen", "Israel",
                       "Turkey", "Egypt", "Jordan", "Saudi Arabia"]
    total = 0
    country_data = {}

    for country in acled_countries:
        try:
            resp = requests.get(
                "https://api.acleddata.com/acled/read",
                params={
                    "key": api_key, "email": email,
                    "country": country,
                    "event_date": run_date,
                    "event_type": "Protests",
                    "limit": 0,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("count", 0)
                country_data[country] = count
                total += count
        except Exception as e:
            logger.debug(f"ACLED {country}: {e}")

    return {
        "value": float(total),
        "raw_json": {"countries": country_data, "source": "acled"},
        "notes": f"ACLED protests: {total} events in ME",
    }


def _gdelt_protest_fallback(run_date: str) -> dict:
    """GDELT-based protest count fallback when ACLED unavailable."""
    from src.tools.gdelt_doc import gdelt_doc_search
    import json

    raw = gdelt_doc_search(
        query="protest demonstration riot unrest",
        mode="artlist", timespan="1d", maxrecords=250,
    )
    try:
        data = json.loads(raw)
        count = data.get("article_count", 0)
    except Exception:
        count = 0

    return {
        "value": float(count),
        "raw_json": {"source": "gdelt_fallback", "article_count": count},
        "notes": f"Protest events (GDELT fallback): {count} articles",
    }
