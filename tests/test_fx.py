"""Tests for FxFetcher and SectorCache."""

from typing import Any

import pytest
from pytest_mock import MockerFixture

from src.exceptions import ValidationError
from src.sector.cache import SectorCache
from src.sector.fx import FxFetcher, FxRates


class TestFxFetcher:
    """Tests for FxFetcher class."""

    def test_fetch_returns_fx_rates(self, mocker: MockerFixture) -> None:
        """Successful fetch returns FxRates with correct values."""

        def mock_fast_info(symbol: str) -> Any:
            ticker = mocker.MagicMock()
            ticker.fast_info = {
                "last_price": 1.34
                if "USD" in symbol
                else 1.23
                if "GBP" in symbol
                else 1.56
                if "EUR" in symbol
                else 0.0091
            }
            return ticker

        mocker.patch("src.sector.fx.yf.Ticker", side_effect=mock_fast_info)
        rates = FxFetcher().fetch()

        assert rates.usdsgd == pytest.approx(1.34)
        assert rates.gbpsgd == pytest.approx(1.23)
        assert rates.eursgd == pytest.approx(1.56)
        assert rates.jpysgd == pytest.approx(0.0091)

    def test_fetch_raises_when_usd_rate_missing(self, mocker: MockerFixture) -> None:
        """ValidationError raised when USDSGD cannot be retrieved."""

        def mock_fast_info(symbol: str) -> Any:
            if "USD" in symbol:
                raise RuntimeError("API error")
            ticker = mocker.MagicMock()
            ticker.fast_info = {
                "last_price": 1.23 if "GBP" in symbol else 1.56 if "EUR" in symbol else 0.0091
            }
            return ticker

        mocker.patch("src.sector.fx.yf.Ticker", side_effect=mock_fast_info)

        with pytest.raises(ValidationError, match="USDSGD=X"):
            FxFetcher().fetch()

    def test_fetch_raises_when_gbp_rate_missing(self, mocker: MockerFixture) -> None:
        """ValidationError raised when GBPSGD cannot be retrieved."""

        def mock_fast_info(symbol: str) -> Any:
            if "GBP" in symbol:
                raise RuntimeError("API error")
            ticker = mocker.MagicMock()
            ticker.fast_info = {
                "last_price": 1.34 if "USD" in symbol else 1.56 if "EUR" in symbol else 0.0091
            }
            return ticker

        mocker.patch("src.sector.fx.yf.Ticker", side_effect=mock_fast_info)

        with pytest.raises(ValidationError, match="GBPSGD=X"):
            FxFetcher().fetch()

    def test_fetch_raises_when_eur_rate_missing(self, mocker: MockerFixture) -> None:
        """ValidationError raised when EURSGD cannot be retrieved."""

        def mock_fast_info(symbol: str) -> Any:
            if "EUR" in symbol:
                raise RuntimeError("API error")
            ticker = mocker.MagicMock()
            ticker.fast_info = {
                "last_price": 1.34 if "USD" in symbol else 1.23 if "GBP" in symbol else 0.0091
            }
            return ticker

        mocker.patch("src.sector.fx.yf.Ticker", side_effect=mock_fast_info)

        with pytest.raises(ValidationError, match="EURSGD=X"):
            FxFetcher().fetch()

    def test_fetch_raises_when_jpy_rate_missing(self, mocker: MockerFixture) -> None:
        """ValidationError raised when JPYSGD cannot be retrieved."""

        def mock_fast_info(symbol: str) -> Any:
            if "JPY" in symbol:
                raise RuntimeError("API error")
            ticker = mocker.MagicMock()
            ticker.fast_info = {
                "last_price": 1.34 if "USD" in symbol else 1.23 if "GBP" in symbol else 1.56
            }
            return ticker

        mocker.patch("src.sector.fx.yf.Ticker", side_effect=mock_fast_info)

        with pytest.raises(ValidationError, match="JPYSGD=X"):
            FxFetcher().fetch()

    def test_fetch_raises_listing_both_when_all_missing(self, mocker: MockerFixture) -> None:
        """Error message names every missing rate when all fail."""
        mocker.patch("src.sector.fx.yf.Ticker", side_effect=RuntimeError("timeout"))

        with pytest.raises(ValidationError) as exc_info:
            FxFetcher().fetch()

        msg = str(exc_info.value)
        assert "USDSGD=X" in msg
        assert "GBPSGD=X" in msg
        assert "EURSGD=X" in msg
        assert "JPYSGD=X" in msg

    def test_fetch_raises_on_zero_rate(self, mocker: MockerFixture) -> None:
        """A zero rate is treated as unavailable."""
        ticker = mocker.MagicMock()
        ticker.fast_info = {"last_price": 0}
        mocker.patch("src.sector.fx.yf.Ticker", return_value=ticker)

        with pytest.raises(ValidationError):
            FxFetcher().fetch()

    def test_fetch_raises_on_none_rate(self, mocker: MockerFixture) -> None:
        """A None rate is treated as unavailable."""
        ticker = mocker.MagicMock()
        ticker.fast_info = {"last_price": None}
        mocker.patch("src.sector.fx.yf.Ticker", return_value=ticker)

        with pytest.raises(ValidationError):
            FxFetcher().fetch()


class TestSectorCache:
    """Tests for SectorCache class."""

    def test_get_sector_returns_none_when_not_cached(self) -> None:
        """get_sector returns None if sector not in cache."""
        assert SectorCache().get_sector("AAPL") is None

    def test_set_and_get_sector_round_trips(self) -> None:
        """set_sector followed by get_sector returns the same value."""
        cache = SectorCache()
        cache.set_sector("AAPL", "Technology")
        assert cache.get_sector("AAPL") == "Technology"

    def test_get_fx_rates_returns_none_when_not_set(self) -> None:
        """get_fx_rates returns None if rates not set."""
        assert SectorCache().get_fx_rates() is None

    def test_set_and_get_fx_rates_round_trips(self) -> None:
        """set_fx_rates followed by get_fx_rates returns the same values."""
        cache = SectorCache()
        rates = FxRates(usdsgd=1.34, gbpsgd=1.23, eursgd=1.56, jpysgd=0.0091)
        cache.set_fx_rates(rates)
        assert cache.get_fx_rates() == rates

    def test_clear_removes_sectors_and_fx_rates(self) -> None:
        """clear removes all cached sectors and FX rates."""
        cache = SectorCache()
        cache.set_sector("AAPL", "Technology")
        cache.set_fx_rates(FxRates(usdsgd=1.34, gbpsgd=1.23, eursgd=1.56, jpysgd=0.0091))
        cache.clear()
        assert cache.get_sector("AAPL") is None
        assert cache.get_fx_rates() is None

    def test_different_tickers_cached_independently(self) -> None:
        """Sectors for different tickers are stored and retrieved independently."""
        cache = SectorCache()
        cache.set_sector("AAPL", "Technology")
        cache.set_sector("D05.SI", "Financials")
        assert cache.get_sector("AAPL") == "Technology"
        assert cache.get_sector("D05.SI") == "Financials"

    def test_overwrite_cached_sector(self) -> None:
        """Setting a sector for a ticker that already has one overwrites it."""
        cache = SectorCache()
        cache.set_sector("AAPL", "Technology")
        cache.set_sector("AAPL", "Consumer Discretionary")
        assert cache.get_sector("AAPL") == "Consumer Discretionary"
