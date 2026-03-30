"""
SENTINEL2 — Airspace Metric Collectors
Metrics: #5 ADS-B Military Flight Activity, #6 GPS Jamming, #20 NOTAMs
"""

import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("sentinel2.metrics.airspace")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}

# ME Flight Information Regions for NOTAM queries
_ME_FIRS = ["OIIX", "ORBB", "OSTT", "OLBB", "LLLL", "OJAC", "OEJD", "LTAA"]


def collect_adsb_military(run_date: str) -> dict:
    """Metric #5: ADS-B military flight activity in ME/Caucasus."""
    # ADS-B Exchange requires paid API — use free OpenSky fallback
    try:
        resp = requests.get(
            "https://opensky-network.org/api/states/all",
            params={"lamin": 12, "lamax": 45, "lomin": 25, "lomax": 65},
            headers=_HEADERS, timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            states = data.get("states", [])
            # Military aircraft heuristic: no callsign or mil-pattern callsign
            mil_patterns = ["RCH", "REACH", "POLO", "EVAC", "DUKE", "NCHO", "IAM"]
            military = [
                s for s in states
                if s[1] and any(p in s[1].strip().upper() for p in mil_patterns)
            ]
            return {
                "value": float(len(military)),
                "raw_json": {"total_aircraft": len(states), "military_count": len(military)},
                "notes": f"ADS-B: {len(military)} military, {len(states)} total in ME airspace",
            }
    except Exception as e:
        logger.warning(f"OpenSky failed: {e}")

    return {"value": None, "raw_json": {}, "notes": "ADS-B data unavailable"}


def collect_gps_jamming(run_date: str) -> dict:
    """Metric #6: GPS jamming incidents (GPSJam.org)."""
    try:
        resp = requests.get(
            "https://gpsjam.org/api/v1/observations",
            params={"date": run_date},
            headers=_HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Filter to ME/Caucasus region
            me_events = [
                e for e in data.get("observations", [])
                if 12 <= e.get("lat", 0) <= 45 and 25 <= e.get("lon", 0) <= 65
            ]
            return {
                "value": float(len(me_events)),
                "raw_json": {"total_global": len(data.get("observations", [])),
                             "me_events": len(me_events)},
                "notes": f"GPS jamming: {len(me_events)} ME events",
            }
    except Exception as e:
        logger.debug(f"GPSJam API failed: {e}")

    # Fallback: scrape GPSJam.org main page
    return {"value": None, "raw_json": {}, "notes": "GPSJam data unavailable"}


def collect_notams(run_date: str) -> dict:
    """Metric #20: Aviation NOTAMs for ME FIRs."""
    total = 0
    fir_counts = {}

    for fir in _ME_FIRS:
        try:
            resp = requests.get(
                "https://notams.aim.faa.gov/notamSearch/search",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    **_HEADERS,
                },
                params={"searchType": "0", "designatorsForLocation": fir},
                timeout=15,
            )
            if resp.status_code == 200:
                # Count NOTAMs in response
                soup = BeautifulSoup(resp.text, "html.parser")
                notam_divs = soup.find_all("div", class_="notamRight")
                count = len(notam_divs)
                fir_counts[fir] = count
                total += count
        except Exception as e:
            logger.debug(f"NOTAM {fir}: {e}")

    return {
        "value": float(total),
        "raw_json": {"fir_counts": fir_counts, "total": total},
        "notes": f"NOTAMs: {total} across {len(fir_counts)} ME FIRs",
    }
