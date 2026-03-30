"""
SENTINEL2 — Internet/Cyber Metric Collectors
Metrics: #3 Cloudflare Radar, #7 Shodan ICS, #16 Censys, #27 CISA Alerts
"""

import os
import logging
import requests

logger = logging.getLogger("sentinel2.metrics.internet")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_ME_COUNTRY_CODES = ["IR", "IQ", "SY", "LB", "YE", "IL", "TR", "SA", "AE", "EG"]


def collect_cloudflare_radar(run_date: str) -> dict:
    """Metric #3: Cloudflare Radar traffic for ME countries."""
    api_key = os.environ.get("CLOUDFLARE_API_KEY", "")
    if not api_key:
        return {"value": None, "raw_json": {}, "notes": "CLOUDFLARE_API_KEY not set"}

    total_traffic = 0
    country_data = {}
    for cc in _ME_COUNTRY_CODES:
        try:
            resp = requests.get(
                f"https://api.cloudflare.com/client/v4/radar/http/summary/traffic",
                headers={"Authorization": f"Bearer {api_key}", **_HEADERS},
                params={"location": cc, "dateRange": "1d"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Extract relative traffic volume
                traffic = data.get("result", {}).get("summary", {}).get("traffic", 0)
                country_data[cc] = traffic
                total_traffic += traffic
        except Exception as e:
            logger.debug(f"Cloudflare {cc}: {e}")

    return {
        "value": float(total_traffic) if total_traffic > 0 else None,
        "raw_json": {"countries": country_data},
        "notes": f"Cloudflare traffic composite: {total_traffic}",
    }


def collect_shodan_ics(run_date: str) -> dict:
    """Metric #7: Shodan ICS/SCADA exposure in ME."""
    api_key = os.environ.get("SHODAN_API_KEY", "")
    if not api_key:
        return {"value": None, "raw_json": {}, "notes": "SHODAN_API_KEY not set"}

    ics_ports = [502, 102, 20000, 47808]  # Modbus, S7, DNP3, BACnet
    total = 0
    port_data = {}

    for port in ics_ports:
        try:
            resp = requests.get(
                f"https://api.shodan.io/shodan/host/count",
                params={
                    "key": api_key,
                    "query": f"port:{port} country:IR,IQ,SA,AE,TR,IL",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                count = resp.json().get("total", 0)
                port_data[str(port)] = count
                total += count
        except Exception as e:
            logger.debug(f"Shodan port {port}: {e}")

    return {
        "value": float(total),
        "raw_json": {"ports": port_data, "total": total},
        "notes": f"Shodan ICS exposure: {total} devices",
    }


def collect_censys_exposed(run_date: str) -> dict:
    """Metric #16: Censys exposed critical infrastructure."""
    api_id = os.environ.get("CENSYS_API_ID", "")
    api_secret = os.environ.get("CENSYS_API_SECRET", "")
    if not api_id or not api_secret:
        return {"value": None, "raw_json": {}, "notes": "Censys credentials not set"}

    try:
        resp = requests.get(
            "https://search.censys.io/api/v2/hosts/aggregate",
            auth=(api_id, api_secret),
            params={
                "q": "services.port: (502 OR 102 OR 20000 OR 47808)",
                "field": "location.country_code",
                "num_buckets": 20,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            buckets = data.get("result", {}).get("buckets", [])
            me_total = sum(
                b.get("count", 0) for b in buckets
                if b.get("key", "") in _ME_COUNTRY_CODES
            )
            return {
                "value": float(me_total),
                "raw_json": {"buckets": buckets, "me_total": me_total},
                "notes": f"Censys ME exposed infrastructure: {me_total}",
            }
    except Exception as e:
        logger.warning(f"Censys failed: {e}")

    return {"value": None, "raw_json": {}, "notes": "Censys query failed"}


def collect_cisa_alerts(run_date: str) -> dict:
    """Metric #27: CISA/INCD cybersecurity alerts."""
    try:
        import feedparser
        feed = feedparser.parse("https://www.cisa.gov/cybersecurity-advisories/all.xml")
        me_keywords = ["iran", "middle east", "scada", "ics", "critical infrastructure",
                       "energy", "oil", "gas", "water"]
        relevant = [
            e for e in feed.entries
            if any(kw in e.get("title", "").lower() + e.get("summary", "").lower()
                   for kw in me_keywords)
        ]
        return {
            "value": float(len(relevant)),
            "raw_json": {"total_alerts": len(feed.entries), "me_relevant": len(relevant),
                         "titles": [e.get("title", "") for e in relevant[:5]]},
            "notes": f"CISA: {len(relevant)} ME-relevant alerts of {len(feed.entries)} total",
        }
    except Exception as e:
        logger.warning(f"CISA feed failed: {e}")
        return {"value": None, "raw_json": {"error": str(e)}, "notes": f"CISA error: {e}"}
