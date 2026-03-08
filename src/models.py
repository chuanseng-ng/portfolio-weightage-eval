"""Domain model: Holding dataclass and market auto-detection logic."""

from dataclasses import dataclass

VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CNY", "SGD", "HKD", "NTD"}


def detect_market(ticker: str) -> str:
    """Detect market from ticker suffix. Returns 'SG', 'UK', or 'US'."""
    upper = ticker.upper()
    if upper.endswith(".SI"):
        return "SG"
    if upper.endswith(".L"):
        return "UK"
    return "US"


@dataclass
class Holding:
    """Represents a single stock holding."""

    ticker: str
    market: str
    quantity: float
    price: float
    currency: str
    sector: str | None = None
    etf_lookthrough: bool = False
