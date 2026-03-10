"""Sector classification for portfolio holdings.

Resolution priority:
  US/UK/EU/JP equities : yFinance only
  SG equities          : yFinance → SGX public API → static CSV → Unclassified
  ETFs                 : look-through (proportional) → ETF Broad Market (fallback)

After any resolution, the SG REIT override is applied:
  if market == "SG" and (ticker contains "REIT" or sector is Financials/Real Estate)
  → reclassify to "REITs"
"""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]
import yfinance as yf  # type: ignore[import-untyped]

from src.models import Holding
from src.sector.cache import SectorCache

YFINANCE_SECTOR_MAP: dict[str, str] = {
    "Technology": "Technology",
    "Healthcare": "Healthcare",
    "Financial Services": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Basic Materials": "Materials",
    "Utilities": "Utilities",
    "Communication Services": "Communication Services",
    "Real Estate": "Real Estate (ex-REITs)",
}

_REIT_OVERRIDE_SECTORS = {"Financials", "Real Estate (ex-REITs)"}
_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "sgx_sectors.csv"
_SGX_API_URL = "https://api.sgx.com/securities/v1.1"
_SGX_API_TIMEOUT = 5  # seconds


class SectorFetcher:
    """Enriches a list of Holdings with sector classifications."""

    def __init__(self, cache: SectorCache) -> None:
        self._cache = cache
        self._csv_data: dict[str, str] | None = None  # loaded once on first use

    # Public API method
    def enrich(self, holdings: list[Holding]) -> list[Holding]:
        """Return new Holding instances with sector and etf_lookthrough set."""
        enriched: list[Holding] = []
        for holding in holdings:
            sector, lookthrough = self._resolve(holding)
            enriched.append(replace(holding, sector=sector, etf_lookthrough=lookthrough))
        return enriched

    # Resolution router method
    def _resolve(self, holding: Holding) -> tuple[str, bool]:
        """Return (sector, etf_lookthrough) for the given holding."""
        cached = self._cache.get_holding(holding.ticker)
        if cached is not None:
            return cached

        if self._is_etf(holding.ticker):
            sector, lookthrough = self._resolve_etf(holding.ticker)
        else:
            sector = self._resolve_equity(holding)
            lookthrough = False

        self._cache.set_holding(holding.ticker, sector, lookthrough)
        return sector, lookthrough

    # ETF resolution method
    def _is_etf(self, ticker: str) -> bool:
        """Return True if yFinance identifies this ticker as an ETF."""
        try:
            info = yf.Ticker(ticker).fast_info
            return str(info.get("quote_type", "")).upper() == "ETF"
        except (OSError, KeyError, TypeError, AttributeError):
            return False

    def _resolve_etf(self, ticker: str) -> tuple[str, bool]:
        """
        Attempt ETF look-through via yFinance fund holdings.

        Returns (sector, etf_lookthrough=True) on success,
        ("ETF Broad Market", False) if constituent data is unavailable.
        """
        try:
            fund_holdings = yf.Ticker(ticker).funds_data.top_holdings
            if fund_holdings is None or fund_holdings.empty:
                return "ETF Broad Market", False

            weights: dict[str, float] = {}
            for constituent_ticker, row in fund_holdings.iterrows():
                weight = float(row.get("holdingPercent", 0.0))
                if weight <= 0:
                    continue
                constituent_sector = self._resolve_equity(
                    Holding(
                        ticker=str(constituent_ticker),
                        market="US",
                        quantity=0,
                        price=0,
                        currency="USD",
                    )
                )
                weights[constituent_sector] = weights.get(constituent_sector, 0.0) + weight

            if not weights:
                return "ETF Broad Market", False

            # Return dominant sector (highest combined weight)
            dominant = max(weights, key=lambda s: weights[s])
            return dominant, True

        except (OSError, AttributeError, TypeError, ValueError, KeyError):
            return "ETF Broad Market", False

    # Equity resolution method
    def _resolve_equity(self, holding: Holding) -> str:
        """Resolve sector for a non-ETF holding."""
        if holding.market in ("US", "UK", "EU", "JP"):
            sector, _ = self._yfinance_sector(holding.ticker)
            return sector if sector else "Unclassified"

        if holding.market == "SG":
            # SG: 4-layer fallback
            sector, long_name = self._yfinance_sector(holding.ticker)
            if not sector:
                sector = (
                    self._sgx_api_sector(holding.ticker)
                    or self._sgx_csv_sector(holding.ticker)
                    or "Unclassified"
                )
                long_name = ""  # longName only available from yFinance layer
            return self._apply_reit_override(holding.ticker, sector, long_name)

        # Unknown market: yFinance only, no SGX fallback or REIT override
        sector, _ = self._yfinance_sector(holding.ticker)
        return sector if sector else "Unclassified"

    # Layer 1 - yFinance
    def _yfinance_sector(self, ticker: str) -> tuple[str | None, str]:
        """Return normalized taxonomy sector from yFinance, or None."""
        try:
            info = yf.Ticker(ticker).info
            raw = info.get("sector", "")
            name = str(info.get("longName", ""))
            return YFINANCE_SECTOR_MAP.get(str(raw)), name
        except (OSError, KeyError, TypeError, AttributeError):
            return None, ""

    # Layer 2 - SGX public API
    def _sgx_api_sector(self, ticker: str) -> str | None:
        """Query SGX public API for sector. Returns normalized string or None."""
        try:
            # Strip .SI suffix for the API query
            code = ticker.upper().removesuffix(".SI")
            response = requests.get(
                _SGX_API_URL,
                params={"code": code},
                timeout=_SGX_API_TIMEOUT,
            )
            if response.status_code != 200:
                return None
            data: Any = response.json()
            raw_sector: str = data.get("data", {}).get("items", [{}])[0].get("category", "")
            return YFINANCE_SECTOR_MAP.get(raw_sector)
        except (OSError, ValueError, KeyError, IndexError):
            return None

    # Layer 3 - Static CSV
    def _load_csv(self) -> dict[str, str]:
        """Load and cache SGX sector CSV. Returns {ticker: sector}."""
        if self._csv_data is not None:
            return self._csv_data
        mapping: dict[str, str] = {}
        try:
            with _CSV_PATH.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    mapping[row["ticker"].strip().upper()] = row["sector"].strip()
        except (OSError, KeyError, csv.Error):
            pass
        self._csv_data = mapping
        return self._csv_data

    def _sgx_csv_sector(self, ticker: str) -> str | None:
        """Look up ticker in bundled SGX CSV. Returns sector string or None."""
        return self._load_csv().get(ticker.upper())

    # REIT override (SG only)
    def _apply_reit_override(self, ticker: str, sector: str, long_name: str = "") -> str:
        """
        Reclassify to 'REITs' if:
          - ticker contains 'REIT' (case-insensitive), OR
          - longName indicates REIT

        This rule applies only to SG holdings (caller's responsibility).
        """
        if "REIT" in ticker.upper():
            return "REITs"
        if sector in _REIT_OVERRIDE_SECTORS:
            # Additional name-based check via yFinance longName
            upper_name = long_name.upper()
            if "REIT" in upper_name or "REAL ESTATE INVEST" in upper_name:
                return "REITs"
        return sector
