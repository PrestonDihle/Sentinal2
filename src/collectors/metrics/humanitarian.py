"""
SENTINEL2 — Humanitarian Metric Collectors
Metrics: #13 UNHCR Displacement, #17 Food Price Index
"""

import logging
import requests

logger = logging.getLogger("sentinel2.metrics.humanitarian")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}


def collect_unhcr_displacement(run_date: str) -> dict:
    """Metric #13: UNHCR displacement figures for ME region."""
    me_countries = ["SYR", "YEM", "IRQ", "LBN", "JOR", "TUR", "EGY", "IRN", "PSE"]
    total = 0
    country_data = {}

    for iso3 in me_countries:
        try:
            resp = requests.get(
                f"https://data.unhcr.org/api/population/{iso3}",
                headers=_HEADERS, timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                pop = data.get("total_population", data.get("persons_of_concern", 0))
                country_data[iso3] = pop
                total += pop
        except Exception as e:
            logger.debug(f"UNHCR {iso3}: {e}")

    # Fallback to ReliefWeb if UNHCR API is down
    if total == 0:
        try:
            resp = requests.get(
                "https://api.reliefweb.int/v1/reports",
                params={
                    "appname": "sentinel2",
                    "filter[field]": "source.shortname",
                    "filter[value]": "UNHCR",
                    "limit": 5,
                    "sort[]": "date:desc",
                },
                headers=_HEADERS, timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("totalCount", 0)
                return {
                    "value": float(count),
                    "raw_json": {"source": "reliefweb_fallback", "report_count": count},
                    "notes": f"UNHCR (ReliefWeb fallback): {count} recent reports",
                }
        except Exception:
            pass

    return {
        "value": float(total) if total > 0 else None,
        "raw_json": {"countries": country_data, "total": total},
        "notes": f"UNHCR displacement: {total:,} persons across {len(country_data)} countries",
    }


def collect_food_prices(run_date: str) -> dict:
    """Metric #17: FAO Food Price Index for ME region."""
    try:
        # FAO FPMA API
        resp = requests.get(
            "https://fpma.fao.org/giews/fpma/datatable/export",
            params={"format": "json", "datatype": "price"},
            headers=_HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "value": float(data.get("index", 0)),
                "raw_json": data,
                "notes": f"FAO Food Price Index: {data.get('index', 'N/A')}",
            }
    except Exception as e:
        logger.debug(f"FAO API: {e}")

    # Fallback: use WFP VAM food prices
    try:
        resp = requests.get(
            "https://api.vam.wfp.org/FoodPrices/PriceMonthly",
            headers=_HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            return {
                "value": None,
                "raw_json": {"source": "wfp_vam"},
                "notes": "WFP VAM data fetched but needs parsing",
            }
    except Exception:
        pass

    return {"value": None, "raw_json": {}, "notes": "Food price data unavailable"}
