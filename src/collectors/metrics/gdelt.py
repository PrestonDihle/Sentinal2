"""
SENTINEL2 — GDELT-Derived Metric Collectors
Metrics: #14 Goldstein Scale, #15 Tone + Volume, #30 Front Page ME Count
Plus 7 new GDELT-derived metrics for expanded coverage.
"""

import logging
import time
import json

import requests

logger = logging.getLogger("sentinel2.metrics.gdelt")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_DELAY = 2

_ME_DYADS = [
    ("Israel", "Iran"), ("Israel", "Lebanon"), ("Saudi Arabia", "Iran"),
    ("Turkey", "Syria"), ("United States", "Iran"), ("Russia", "Israel"),
    ("Iran", "Iraq"), ("Yemen", "Saudi Arabia"),
]
_ME_COUNTRIES = ["Iran", "Israel", "Syria", "Yemen", "Lebanon", "Iraq", "Turkey", "Saudi Arabia"]


def _gdelt_tone(query: str) -> float | None:
    """Get average tone from GDELT DOC API timelinetone mode."""
    try:
        resp = requests.get(_GDELT_DOC, params={
            "query": query, "mode": "timelinetone", "timespan": "1d", "format": "json",
        }, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        timeline = data.get("timeline", [])
        if timeline and isinstance(timeline[0], dict):
            series = timeline[0].get("data", [])
            values = [float(p["value"]) for p in series if "value" in p]
            if values:
                return round(sum(values) / len(values), 3)
    except Exception as e:
        logger.debug(f"GDELT tone '{query}': {e}")
    return None


def _gdelt_volume(query: str) -> float | None:
    """Get article volume from GDELT DOC API timelinevol mode."""
    try:
        resp = requests.get(_GDELT_DOC, params={
            "query": query, "mode": "timelinevol", "timespan": "1d", "format": "json",
        }, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        timeline = data.get("timeline", [])
        if timeline and isinstance(timeline[0], dict):
            series = timeline[0].get("data", [])
            values = [float(p["value"]) for p in series if "value" in p]
            if values:
                return round(sum(values), 1)
    except Exception as e:
        logger.debug(f"GDELT volume '{query}': {e}")
    return None


def _gdelt_artcount(query: str, theme: str = None) -> int:
    """Count articles matching query via GDELT DOC artlist mode."""
    full_q = f"{query} theme:{theme}" if theme else query
    try:
        resp = requests.get(_GDELT_DOC, params={
            "query": full_q, "mode": "artlist", "maxrecords": 250,
            "timespan": "1d", "format": "json",
        }, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return len(data.get("articles", []))
    except Exception:
        return 0


def collect_goldstein_scale(run_date: str) -> dict:
    """Metric #14: GDELT Goldstein (tone proxy) for ME dyads."""
    dyad_data = {}
    scores = []
    for a1, a2 in _ME_DYADS:
        tone = _gdelt_tone(f"{a1} {a2}")
        dyad_data[f"{a1}-{a2}"] = tone
        if tone is not None:
            scores.append(tone)
        time.sleep(_GDELT_DELAY)

    avg = round(sum(scores) / len(scores), 3) if scores else None
    return {
        "value": avg,
        "raw_json": {"dyad_tones": dyad_data, "overall_avg": avg},
        "notes": f"Goldstein proxy: {avg} ({len(scores)} dyads)",
    }


def collect_tone_volume(run_date: str) -> dict:
    """Metric #15: GDELT tone + article volume for ME."""
    country_data = {}
    total_vol = 0

    for country in _ME_COUNTRIES:
        tone = _gdelt_tone(country)
        time.sleep(_GDELT_DELAY)
        vol = _gdelt_volume(country)
        time.sleep(_GDELT_DELAY)
        country_data[country] = {"tone": tone, "volume": vol}
        if vol:
            total_vol += vol

    return {
        "value": float(total_vol) if total_vol > 0 else None,
        "raw_json": {"countries": country_data, "total_volume": total_vol},
        "notes": f"GDELT ME volume: {total_vol}",
    }


def collect_front_page_count(run_date: str) -> dict:
    """Metric #30: GDELT front page ME article count."""
    queries = [
        "Iran military", "Israel strike", "Yemen Houthi",
        "Hezbollah Lebanon", "Syria conflict", "Saudi Arabia Iran",
    ]
    total = 0
    query_data = {}
    for q in queries:
        count = _gdelt_artcount(q)
        query_data[q] = count
        total += count
        time.sleep(_GDELT_DELAY)

    return {
        "value": float(total),
        "raw_json": {"queries": query_data, "total": total},
        "notes": f"GDELT front page ME: {total} articles",
    }


# ── 7 New GDELT-Derived Metrics ─────────────────────────────────────

def collect_wmd_mentions(run_date: str) -> dict:
    """New: WMD/Proliferation mentions by country."""
    count = _gdelt_artcount("nuclear chemical biological weapon proliferation", "WMD")
    time.sleep(_GDELT_DELAY)
    return {
        "value": float(count),
        "raw_json": {"wmd_articles": count},
        "notes": f"WMD mentions: {count} articles",
    }


def collect_protest_events(run_date: str) -> dict:
    """New: Protest/civil unrest events via GDELT CAMEO code 14."""
    count = _gdelt_artcount("protest demonstration riot civil unrest Middle East")
    time.sleep(_GDELT_DELAY)
    return {
        "value": float(count),
        "raw_json": {"protest_articles": count},
        "notes": f"Protest events: {count} articles",
    }


def collect_diplomatic_cooperation(run_date: str) -> dict:
    """New: Diplomatic cooperation signals (positive Goldstein)."""
    tone = _gdelt_tone("diplomacy peace agreement ceasefire Middle East")
    time.sleep(_GDELT_DELAY)
    return {
        "value": tone,
        "raw_json": {"cooperation_tone": tone},
        "notes": f"Diplomatic cooperation tone: {tone}",
    }


def collect_sanctions_coverage(run_date: str) -> dict:
    """New: Sanctions-related coverage."""
    count = _gdelt_artcount("sanctions Iran Russia Middle East", "ECON_SANCTIONS")
    time.sleep(_GDELT_DELAY)
    return {
        "value": float(count),
        "raw_json": {"sanctions_articles": count},
        "notes": f"Sanctions coverage: {count} articles",
    }


def collect_refugee_mentions(run_date: str) -> dict:
    """New: Refugee/displacement mentions."""
    count = _gdelt_artcount("refugee displacement migration Syria Yemen Iraq", "REFUGEES")
    time.sleep(_GDELT_DELAY)
    return {
        "value": float(count),
        "raw_json": {"refugee_articles": count},
        "notes": f"Refugee mentions: {count} articles",
    }


def collect_leadership_changes(run_date: str) -> dict:
    """New: Leadership change signals."""
    count = _gdelt_artcount("leader succession regime change appointment Middle East", "LEADER")
    time.sleep(_GDELT_DELAY)
    return {
        "value": float(count),
        "raw_json": {"leadership_articles": count},
        "notes": f"Leadership change signals: {count} articles",
    }


def collect_military_exercises(run_date: str) -> dict:
    """New: Military exercise activity."""
    count = _gdelt_artcount("military exercise drill naval joint Middle East", "MILITARY_EXERCISE")
    time.sleep(_GDELT_DELAY)
    return {
        "value": float(count),
        "raw_json": {"exercise_articles": count},
        "notes": f"Military exercises: {count} articles",
    }
