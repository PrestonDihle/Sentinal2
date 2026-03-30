"""
SENTINEL2 — GDELT GKG (Global Knowledge Graph) Bulk Download Tool

Downloads 15-minute GKG CSV exports from GDELT, filters by monitored
countries and themes, and extracts entities, persons, organizations,
locations, and tone.

Bulk CSV URL pattern:
    http://data.gdeltproject.org/gdeltv2/{YYYYMMDDHHMMSS}.gkg.csv.zip

GKG fields (tab-separated):
    0: GKGRECORDID
    1: DATE (YYYYMMDDHHMMSS)
    2: SourceCollectionIdentifier
    3: SourceCommonName
    4: DocumentIdentifier (URL)
    5: Counts
    6: V2Counts
    7: Themes (semicolon-separated)
    8: V2EnhancedThemes
    9: Locations
    10: V2EnhancedLocations
    11: Persons
    12: V2EnhancedPersons
    13: Organizations
    14: V2EnhancedOrganizations
    15: V2Tone (comma-separated: tone,pos,neg,polarity,activity,self/group,wordcount)
    16: V2EnhancedDates
    17: V2GCAM
    18: V2SharingImage
    19: V2RelatedImages
    20: V2SocialImageEmbeds
    21: V2SocialVideoEmbeds
    22: V2Quotations
    23: V2AllNames
    24: V2Amounts
    25: V2TranslationInfo
    26: V2Extras (SourceURL)
"""

import io
import csv
import json
import time
import logging
import zipfile
from datetime import datetime, timedelta
from typing import Optional

import requests
from crewai.tools import BaseTool

from nais.reference import COUNTRIES, COUNTRY_CODES

logger = logging.getLogger("sentinel2.tools.gdelt_gkg")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}
_GKG_BASE = "http://data.gdeltproject.org/gdeltv2"

# FIPS codes for monitored countries (for location filtering)
_MONITORED_FIPS = set(COUNTRY_CODES.values())

# Key GDELT themes relevant to our PIRs
_PIR_THEMES = {
    "PIR1": [
        "MILITARY", "TERROR", "KILL", "PROTEST", "ARMEDCONFLICT",
        "WMD", "CYBER_ATTACK", "ECON_BANKRUPTCY", "REFUGEES",
    ],
    "PIR2": [
        "MARITIME_INCIDENT", "BLOCKADE", "MILITARY_EXERCISE",
        "ALLIANCE", "SANCTIONS", "ECON_OIL",
    ],
    "PIR3": [
        "CEASEFIRE", "PEACE", "DIPLOMACY", "MEDIATION",
        "ECON_TRADE", "HUMANITARIAN_AID",
    ],
    "PIR4": [
        "RUSSIA", "CHINA", "ARMS_SALE", "ECON_SANCTIONS",
        "TECHNOLOGY_TRANSFER",
    ],
}


class GDELTGKGTool(BaseTool):
    """Download and filter GDELT GKG bulk exports."""

    name: str = "gdelt_gkg_download"
    description: str = (
        "Download GDELT Global Knowledge Graph (GKG) 15-minute bulk CSV "
        "exports. Returns pre-extracted themes, entities, persons, "
        "organizations, locations, and tone. "
        "Input: JSON with 'timestamp' (YYYYMMDDHHMMSS) or 'hours_back' (int)."
    )

    def _run(self, input_str: str) -> str:
        try:
            params = json.loads(input_str) if isinstance(input_str, str) else input_str
        except json.JSONDecodeError:
            params = {"hours_back": 24}

        hours_back = params.get("hours_back", 24)
        records = download_gkg_range(hours_back=hours_back)
        filtered = filter_gkg_records(records)
        return json.dumps({
            "total_downloaded": len(records),
            "filtered_count": len(filtered),
            "records": filtered[:100],  # Cap for context window
        })


def _round_to_15min(dt: datetime) -> str:
    """Round datetime down to nearest 15-minute interval for GKG filename."""
    minute = (dt.minute // 15) * 15
    rounded = dt.replace(minute=minute, second=0, microsecond=0)
    return rounded.strftime("%Y%m%d%H%M%S")


def download_gkg_file(timestamp: str) -> list[dict]:
    """
    Download a single GKG CSV file for the given timestamp.

    Args:
        timestamp: YYYYMMDDHHMMSS format (must align to 15-min intervals)

    Returns:
        List of parsed GKG records as dicts.
    """
    url = f"{_GKG_BASE}/{timestamp}.gkg.csv.zip"
    records = []

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=60)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                if name.endswith(".csv"):
                    with zf.open(name) as f:
                        text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
                        reader = csv.reader(text, delimiter="\t")
                        for row in reader:
                            if len(row) < 16:
                                continue
                            record = _parse_gkg_row(row)
                            if record:
                                records.append(record)

        logger.info(f"GKG {timestamp}: {len(records)} records")
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            logger.debug(f"GKG file not found: {timestamp}")
        else:
            logger.warning(f"GKG download error {timestamp}: {e}")
    except Exception as e:
        logger.warning(f"GKG parse error {timestamp}: {e}")

    return records


def _parse_gkg_row(row: list) -> Optional[dict]:
    """Parse a single GKG CSV row into a structured dict."""
    try:
        # Extract tone (field 15)
        tone_parts = row[15].split(",") if row[15] else []
        tone = float(tone_parts[0]) if tone_parts else 0.0

        # Extract themes (field 7)
        themes = [t.strip() for t in row[7].split(";") if t.strip()] if row[7] else []

        # Extract persons (field 11)
        persons = [p.strip() for p in row[11].split(";") if p.strip()] if row[11] else []

        # Extract organizations (field 13)
        orgs = [o.strip() for o in row[13].split(";") if o.strip()] if row[13] else []

        # Extract locations (field 9) — format: type#name#countrycode#...
        locations = []
        if row[9]:
            for loc in row[9].split(";"):
                parts = loc.split("#")
                if len(parts) >= 3:
                    locations.append({
                        "type": parts[0],
                        "name": parts[1],
                        "country_code": parts[2],
                    })

        return {
            "gkg_id": row[0],
            "date": row[1],
            "source": row[3],
            "url": row[4],
            "themes": themes,
            "locations": locations,
            "persons": persons,
            "organizations": orgs,
            "tone": round(tone, 2),
            "word_count": int(tone_parts[6]) if len(tone_parts) > 6 and tone_parts[6].strip().isdigit() else 0,
        }
    except Exception as e:
        logger.debug(f"GKG row parse error: {e}")
        return None


def download_gkg_range(hours_back: int = 24, max_files: int = 96) -> list[dict]:
    """
    Download GKG files for the last N hours.
    Each hour has 4 files (every 15 min), so 24h = 96 files max.
    """
    now = datetime.utcnow()
    all_records = []
    files_fetched = 0

    for i in range(0, hours_back * 4):
        if files_fetched >= max_files:
            break
        dt = now - timedelta(minutes=15 * i)
        ts = _round_to_15min(dt)
        records = download_gkg_file(ts)
        all_records.extend(records)
        files_fetched += 1
        time.sleep(0.5)  # Be polite

    logger.info(f"GKG range: {files_fetched} files, {len(all_records)} total records")
    return all_records


def filter_gkg_records(
    records: list[dict],
    country_codes: Optional[set] = None,
    themes: Optional[list[str]] = None,
) -> list[dict]:
    """
    Filter GKG records by monitored countries and/or themes.

    Args:
        records: Raw GKG records
        country_codes: Set of FIPS codes to include (default: monitored countries)
        themes: List of theme substrings to match (default: all PIR themes)

    Returns:
        Filtered records relevant to SENTINEL2 coverage area.
    """
    if country_codes is None:
        country_codes = _MONITORED_FIPS

    if themes is None:
        themes = []
        for pir_themes in _PIR_THEMES.values():
            themes.extend(pir_themes)

    theme_set = set(t.upper() for t in themes)
    filtered = []

    for record in records:
        # Check country match via locations
        country_match = False
        for loc in record.get("locations", []):
            if loc.get("country_code", "").upper() in country_codes:
                country_match = True
                break

        # Check theme match
        theme_match = False
        for record_theme in record.get("themes", []):
            for target_theme in theme_set:
                if target_theme in record_theme.upper():
                    theme_match = True
                    break
            if theme_match:
                break

        if country_match or theme_match:
            filtered.append(record)

    logger.info(f"GKG filter: {len(records)} → {len(filtered)} records")
    return filtered


def get_pir_themes() -> dict:
    """Return the PIR-to-theme mapping."""
    return _PIR_THEMES
