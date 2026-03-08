"""FX rates and fetcher for external API (yahoo finance)."""

from dataclasses import dataclass

import yfinance as yf  # type: ignore[import-untyped]

from src.exceptions import ValidationError


@dataclass(frozen=True)
class FxRates:
    """Represents FX rates relative to SGD."""

    usdsgd: float
    gbpsgd: float
    eursgd: float
    jpysgd: float


class FxFetcher:
    """Fetches live FX rates from yFinance."""

    _SYMBOLS: dict[str, str] = {
        "usdsgd": "USDSGD=X",
        "gbpsgd": "GBPSGD=X",
        "eursgd": "EURSGD=X",
        "jpysgd": "JPYSGD=X",
    }

    def fetch(self) -> FxRates:
        """Fetch FX rates from yFinance and return as FxRates dataclass."""
        rates: dict[str, float] = {}
        missing: list[str] = []

        for field, symbol in self._SYMBOLS.items():
            try:
                price = yf.Ticker(symbol).fast_info["last_price"]
                if price is None or price <= 0:
                    raise ValueError(f"Invalid price for {symbol}: {price}")
                rates[field] = float(price)
            except Exception:
                missing.append(symbol)

        if missing:
            raise ValidationError(f"Failed to fetch FX rates for: {', '.join(missing)}")

        return FxRates(**rates)
