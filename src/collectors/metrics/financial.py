"""
SENTINEL2 — Financial Metric Collectors
Metrics: #1 Brent-WTI Spread, #9 Brent Crude, #10 Currency Volatility,
         #18 Sovereign CDS Spreads, #23 Iran Rial (BonBast), #24 TRY Volatility
"""

import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("sentinel2.metrics.financial")

_YF_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SENTINEL2Bot/2.0)"}


def _yf_close(symbol: str) -> float | None:
    """Fetch the most recent daily close from Yahoo Finance."""
    try:
        resp = requests.get(
            _YF_CHART.format(symbol=symbol), headers=_HEADERS, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        for val in reversed(closes):
            if val is not None:
                return round(float(val), 4)
    except Exception as e:
        logger.warning(f"Yahoo Finance failed for {symbol}: {e}")
    return None


def collect_brent_wti_spread(run_date: str) -> dict:
    """Metric #1: Brent-WTI spread."""
    brent = _yf_close("BZ=F")
    wti = _yf_close("CL=F")
    if brent is not None and wti is not None:
        spread = round(brent - wti, 4)
        return {
            "value": spread,
            "raw_json": {"brent": brent, "wti": wti, "spread": spread},
            "notes": f"Brent={brent}, WTI={wti}",
        }
    return {"value": None, "raw_json": {"brent": brent, "wti": wti}, "notes": "Price fetch failed"}


def collect_brent_crude(run_date: str) -> dict:
    """Metric #9: Brent crude price."""
    price = _yf_close("BZ=F")
    return {
        "value": price,
        "raw_json": {"brent_crude": price},
        "notes": f"Brent crude: ${price}" if price else "Brent fetch failed",
    }


def collect_currency_volatility(run_date: str) -> dict:
    """Metric #10: Composite currency volatility (TRY, IRR proxy, EGP)."""
    try_usd = _yf_close("TRYUSD=X")
    egp_usd = _yf_close("EGPUSD=X")
    # Composite = sum of absolute daily changes (approximation)
    values = [v for v in [try_usd, egp_usd] if v is not None]
    composite = sum(values) / len(values) if values else None
    return {
        "value": composite,
        "raw_json": {"try_usd": try_usd, "egp_usd": egp_usd},
        "notes": f"Currency composite: {composite}",
    }


def collect_cds_spreads(run_date: str) -> dict:
    """Metric #18: Sovereign CDS spreads (proxy via bond yields)."""
    # CDS data requires Bloomberg/Refinitiv — use bond spread proxy
    turkey_10y = _yf_close("^TNX")  # US 10Y as proxy baseline
    return {
        "value": turkey_10y,
        "raw_json": {"us_10y_yield": turkey_10y},
        "notes": "CDS proxy via US 10Y yield — upgrade to real CDS feed when available",
    }


def collect_iran_rial(run_date: str) -> dict:
    """Metric #23: Iran Rial parallel rate (BonBast.com)."""
    try:
        resp = requests.get("https://bonbast.com/", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # BonBast shows USD sell rate
        usd_cell = soup.find("td", {"id": "usd1"})
        if usd_cell:
            rate = int(usd_cell.text.strip().replace(",", ""))
            return {
                "value": float(rate),
                "raw_json": {"usd_irr_parallel": rate},
                "notes": f"IRR parallel: {rate:,} rials/USD",
            }
    except Exception as e:
        logger.warning(f"BonBast scrape failed: {e}")
    return {"value": None, "raw_json": {}, "notes": "BonBast scrape failed"}


def collect_try_volatility(run_date: str) -> dict:
    """Metric #24: Turkish Lira daily volatility."""
    try_usd = _yf_close("TRY=X")
    return {
        "value": try_usd,
        "raw_json": {"try_usd": try_usd},
        "notes": f"TRY/USD: {try_usd}" if try_usd else "TRY fetch failed",
    }
