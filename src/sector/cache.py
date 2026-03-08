"""In-memory cache for sector lookups and FX rates within a single run."""

from src.sector.fx import FxRates


class SectorCache:
    """
    Caches sector strings and FX rates for the duration of a single run.

    Avoids redundant yFinance / SGX API calls when the same ticker
    appears multiple times in the portfolio.
    """

    def __init__(self) -> None:
        self._sectors: dict[str, str] = {}
        self.fx_rates: FxRates | None = None

    def get_sector(self, ticker: str) -> str | None:
        """Return the sector for the given ticker, or None if not found."""
        return self._sectors.get(ticker)

    def set_sector(self, ticker: str, sector: str) -> None:
        """Cache the sector for the given ticker."""
        self._sectors[ticker] = sector

    def get_fx_rates(self) -> FxRates | None:
        """Return the cached FX rates, or None if not available."""
        return self.fx_rates

    def set_fx_rates(self, rates: FxRates) -> None:
        """Cache the FX rates."""
        self.fx_rates = rates

    def clear(self) -> None:
        """Clear all cached data."""
        self._sectors.clear()
        self.fx_rates = None
