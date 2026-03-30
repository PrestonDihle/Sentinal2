"""
SENTINEL2 — Maritime Metric Collectors
Metrics: #11 AIS Dark Ships, #12 Suez Transit Count,
         #22 Red Sea Diversions, #26 Port Activity
"""

import logging
import requests

logger = logging.getLogger("sentinel2.metrics.maritime")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}


def collect_dark_ships(run_date: str) -> dict:
    """Metric #11: Maritime AIS dark ships in Gulf/Red Sea."""
    # MarineTraffic/AIS data requires commercial API
    # Use IMF PortWatch as proxy for shipping anomalies
    try:
        resp = requests.get(
            "https://portwatch.imf.org/api/v1/port-calls",
            params={"region": "Middle East", "date": run_date},
            headers=_HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "value": float(len(data.get("results", []))),
                "raw_json": data,
                "notes": "AIS dark ships proxy via IMF PortWatch",
            }
    except Exception as e:
        logger.debug(f"PortWatch dark ships: {e}")

    return {"value": None, "raw_json": {}, "notes": "AIS dark ship data unavailable — requires commercial API"}


def collect_suez_transits(run_date: str) -> dict:
    """Metric #12: Suez Canal daily transit count."""
    # Primary: IMF PortWatch Suez data
    try:
        resp = requests.get(
            "https://portwatch.imf.org/api/v1/chokepoints/suez",
            params={"date": run_date},
            headers=_HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            transits = data.get("transit_count", data.get("count", 0))
            return {
                "value": float(transits),
                "raw_json": data,
                "notes": f"Suez transits: {transits}",
            }
    except Exception as e:
        logger.debug(f"Suez transit: {e}")

    return {"value": None, "raw_json": {}, "notes": "Suez transit data unavailable"}


def collect_red_sea_diversions(run_date: str) -> dict:
    """Metric #22: Red Sea shipping diversions (Cape route vs Suez)."""
    # This metric compares Suez traffic to historical baseline
    # When diversions increase, Suez count drops
    suez_data = collect_suez_transits(run_date)
    suez_count = suez_data.get("value")

    if suez_count is not None:
        # Historical average ~55 transits/day
        historical_avg = 55.0
        diversion_pct = max(0, round((1 - suez_count / historical_avg) * 100, 1))
        return {
            "value": diversion_pct,
            "raw_json": {"suez_count": suez_count, "historical_avg": historical_avg,
                         "diversion_percent": diversion_pct},
            "notes": f"Red Sea diversions: ~{diversion_pct}% traffic avoiding Suez",
        }

    return {"value": None, "raw_json": {}, "notes": "Diversion data unavailable"}


def collect_port_activity(run_date: str) -> dict:
    """Metric #26: Port activity at Jebel Ali and Baku."""
    ports = {"jebel_ali": "AEJEA", "baku": "AZBAK"}
    results = {}
    total = 0

    for name, code in ports.items():
        try:
            resp = requests.get(
                f"https://portwatch.imf.org/api/v1/port-calls/{code}",
                params={"date": run_date},
                headers=_HEADERS, timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("count", 0)
                results[name] = count
                total += count
        except Exception as e:
            logger.debug(f"Port {name}: {e}")

    return {
        "value": float(total) if total > 0 else None,
        "raw_json": {"ports": results},
        "notes": f"Port activity: {total} calls at Jebel Ali + Baku",
    }
