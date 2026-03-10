"""Tests for SectorFetcher - all external calls mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
from pytest_mock import MockerFixture

from src.models import Holding
from src.sector.cache import SectorCache
from src.sector.fetcher import YFINANCE_SECTOR_MAP, SectorFetcher


# Helper function
def _make_holding(
    ticker: str = "AAPL",
    market: str = "US",
    currency: str = "USD",
) -> Holding:
    return Holding(ticker=ticker, market=market, quantity=10, price=100.0, currency=currency)


def _fetcher(cache: SectorCache | None = None) -> SectorFetcher:
    return SectorFetcher(cache or SectorCache())


# US / UK / EU / JP Equity via yFinance
# Currently only test US & UK
class TestUsUkEquities:
    """Test class for US & UK equities"""

    def test_us_ticker_mapped_from_yfinance(self, mocker: MockerFixture) -> None:
        """US ticker resolved via yFinance and mapped to taxonomy."""
        _mock_yf_info(mocker, "AAPL", sector="Technology", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("AAPL", "US")])
        assert result[0].sector == "Technology"
        assert result[0].etf_lookthrough is False

    def test_uk_ticker_mapped_from_yfinance(self, mocker: MockerFixture) -> None:
        """UK ticker resolved via yFinance and mapped to taxonomy"""
        _mock_yf_info(mocker, "LLOY.L", sector="Financial Services", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("LLOY.L", "UK", "GBP")])
        assert result[0].sector == "Financials"

    def test_unknown_yfinance_sector_maps_to_unclassified(self, mocker: MockerFixture) -> None:
        """yFinance sector string not in taxonomy map -> Unclassified."""
        _mock_yf_info(mocker, "AAPL", sector="Widget", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("AAPL", "US")])
        assert result[0].sector == "Unclassified"

    def test_yfinance_raises_returns_unclassified(self, mocker: MockerFixture) -> None:
        """yFinance exception -> Unclassified, no exception raised."""
        mocker.patch("src.sector.fetcher.yf.Ticker", side_effect=OSError("timeout"))
        result = _fetcher().enrich([_make_holding("AAPL", "US")])
        assert result[0].sector == "Unclassified"
        assert result[0].etf_lookthrough is False


# SGX fallback chain


class TestSgxFallbackChain:
    """Test class for SGX fallback chain"""

    def test_layer1_yfinance_resolves_sg_ticker(self, mocker: MockerFixture) -> None:
        """Layer 1: .SI ticker resolved via yFinance"""
        _mock_yf_info(mocker, "D05.SI", sector="Financial Services", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("D05.SI", "SG", "SGD")])
        assert result[0].sector == "Financials"

    def test_layer2_sgx_api_used_when_yfinance_fails(self, mocker: MockerFixture) -> None:
        """Layer 2: SGX API used when yFinance returns no sector."""
        _mock_yf_info(mocker, "X99.SI", sector=None, quote_type="EQUITY")
        _mock_sgx_api(mocker, "Financial Services")
        result = _fetcher().enrich([_make_holding("X99.SI", "SG", "SGD")])
        assert result[0].sector == "Financials"

    def test_layer3_csv_used_when_api_fails(self, mocker: MockerFixture) -> None:
        """Layer 3: CSV used when yFinance and SGX API both fail."""
        _mock_yf_info(mocker, "C31.SI", sector=None, quote_type="EQUITY")
        _mock_sgx_api(mocker, None)
        mocker.patch.object(SectorFetcher, "_load_csv", return_value={"C31.SI": "REITs"})
        result = _fetcher().enrich([_make_holding("C31.SI", "SG", "SGD")])
        assert result[0].sector == "REITs"

    def test_layer4_unclassified_when_all_fail(self, mocker: MockerFixture) -> None:
        """Layer 4: Unclassified when yFinance, SGX API, and CSV all fail."""
        _mock_yf_info(mocker, "Z99.SI", sector=None, quote_type="EQUITY")
        _mock_sgx_api(mocker, None)
        mocker.patch.object(SectorFetcher, "_load_csv", return_value={})
        result = _fetcher().enrich([_make_holding("Z99.SI", "SG", "SGD")])
        assert result[0].sector == "Unclassified"

    def test_sgx_api_non_200_falls_through_to_csv(self, mocker: MockerFixture) -> None:
        """Non-200 SGX API response treated as layer 2 miss."""
        _mock_yf_info(mocker, "X99.SI", sector=None, quote_type="EQUITY")
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mocker.patch("src.sector.fetcher.requests.get", return_value=mock_resp)
        mocker.patch.object(SectorFetcher, "_load_csv", return_value={"X99.SI": "Industrials"})
        result = _fetcher().enrich([_make_holding("X99.SI", "SG", "SGD")])
        assert result[0].sector == "Industrials"

    def test_sgx_api_timeout_falls_through_to_csv(self, mocker: MockerFixture) -> None:
        """SGX API timeout treated as layer 2 miss."""
        _mock_yf_info(mocker, "X99.SI", sector=None, quote_type="EQUITY")
        mocker.patch("src.sector.fetcher.requests.get", side_effect=TimeoutError)
        mocker.patch.object(SectorFetcher, "_load_csv", return_value={"X99.SI": "Industrials"})
        result = _fetcher().enrich([_make_holding("X99.SI", "SG", "SGD")])
        assert result[0].sector == "Industrials"


# REIT override


class TestReitOverride:
    """Test class for REIT category override"""

    def test_reit_in_ticker_name_overrides_financials(self, mocker: MockerFixture) -> None:
        """'REIT' in ticker -> REITs regardless of yFinance classification."""
        _mock_yf_info(mocker, "CREIT.SI", sector="Financial Services", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("CREIT.SI", "SG", "SGD")])
        assert result[0].sector == "REITs"

    def test_reit_name_in_long_name_overrides_real_estate(self, mocker: MockerFixture) -> None:
        """yFinance longName contains 'REIT' -> REITs overrides Real Estate."""
        _mock_yf_info(
            mocker,
            "C31.SI",
            sector="Real Estate",
            quote_type="EQUITY",
            long_name="CapitaLand Integrated Commercial REIT",
        )
        result = _fetcher().enrich([_make_holding("C31.SI", "SG", "SGD")])
        assert result[0].sector == "REITs"

    def test_sg_financials_without_reit_indicators_not_overridden(
        self, mocker: MockerFixture
    ) -> None:
        """SG Financials holding with no REIT indicators stays Financials."""
        _mock_yf_info(
            mocker,
            "D05.SI",
            sector="Financial Services",
            quote_type="EQUITY",
            long_name="DBS Group Holdings Ltd",
        )
        result = _fetcher().enrich([_make_holding("D05.SI", "SG", "SGD")])
        assert result[0].sector == "Financials"

    def test_us_reit_ticker_not_overridden(self, mocker: MockerFixture) -> None:
        """REIT override does NOT apply to US market holdings."""
        _mock_yf_info(mocker, "VNQ", sector="Real Estate", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("VNQ", "US")])
        assert result[0].sector == "Real Estate (ex-REITs)"


# ETF look-through


class TestEtfLookthrough:
    """Test class for ETF look-through"""

    # TODO: Change etf-lookthrough to calculate top 20 fund holding sector %
    def test_etf_with_holdings_use_lookthrough(self, mocker: MockerFixture) -> None:
        """ETF with available fund holdings -> etf_lookthrough=True, dominant sector."""
        df = pd.DataFrame({"holdingPercent": [0.07, 0.06]}, index=["AAPL", "MSFT"])

        voo_mock = MagicMock()
        voo_mock.fast_info = {"quote_type": "ETF"}
        voo_mock.funds_data.top_holdings = df

        equity_mock = MagicMock()
        equity_mock.fast_info = {"quote_type": "EQUITY"}
        equity_mock.info = {"sector": "Technology", "longName": ""}

        def side_effect(ticker: str) -> Any:
            return voo_mock if ticker == "VOO" else equity_mock

        mocker.patch("src.sector.fetcher.yf.Ticker", side_effect=side_effect)
        result = _fetcher().enrich([_make_holding("VOO", "US")])

        assert result[0].etf_lookthrough is True
        assert result[0].sector == "Technology"

    def test_etf_without_holdings_falls_back_to_broad_market(self, mocker: MockerFixture) -> None:
        """ETF with no fund holdings data -> ETF Broad Market, etf_lookthrough=False."""
        _mock_yf_etf(mocker, "VOO", top_holdings=None)
        result = _fetcher().enrich([_make_holding("VOO", "US")])
        assert result[0].sector == "ETF Broad Market"
        assert result[0].etf_lookthrough is False

    def test_etf_lookthrough_error_falls_back_to_broad_market(self, mocker: MockerFixture) -> None:
        """Exception during look-through -> ETF Broad Market, no exception raised."""
        ticker_mock = MagicMock()
        ticker_mock.fast_info = {"quote_type": "ETF"}
        ticker_mock.funds_data.top_holdings = None
        mocker.patch("src.sector.fetcher.yf.Ticker", return_value=ticker_mock)
        result = _fetcher().enrich([_make_holding("VOO", "US")])
        assert result[0].sector == "ETF Broad Market"
        assert result[0].etf_lookthrough is False

    def test_non_etf_has_lookthrough_false(self, mocker: MockerFixture) -> None:
        """Non-ETF holding always has etf_lookthrough=False."""
        _mock_yf_info(mocker, "AAPL", sector="Technology", quote_type="EQUITY")
        result = _fetcher().enrich([_make_holding("AAPL", "US")])
        assert result[0].etf_lookthrough is False


# Caching behavior


class TestCaching:
    """Test class for caching"""

    def test_second_call_for_same_ticker_hits_cache(self, mocker: MockerFixture) -> None:
        """yFinance called only once when same ticker appears twice."""
        ticker_mock = MagicMock()
        ticker_mock.fast_info = {"quote_type": "EQUITY"}
        ticker_mock.info = {"sector": "Technology", "longName": ""}

        yf_patch = mocker.patch("src.sector.fetcher.yf.Ticker", return_value=ticker_mock)

        cache = SectorCache()
        SectorFetcher(cache).enrich([_make_holding("AAPL"), _make_holding("AAPL")])

        # First AAPL: _is_etf + _yfinance_sector = 2 calls max
        # Second AAPL: cache hit -> 0 additional calls
        assert yf_patch.call_count <= 2

    def test_cache_populated_after_enrich(self, mocker: MockerFixture) -> None:
        """Sector is stored in cache after enrich."""
        _mock_yf_info(mocker, "AAPL", sector="Technology", quote_type="EQUITY")
        cache = SectorCache()
        SectorFetcher(cache).enrich([_make_holding("AAPL")])
        assert cache.get_holding("AAPL") == ("Technology", False)


# Edge cases


class TestEdgeCases:
    """Test class for edge cases"""

    def test_empty_holdings_returns_empty_list(self) -> None:
        """Empty holdings should return empty list."""
        result = _fetcher().enrich([])
        assert not result

    def test_input_holdings_not_mutated(self, mocker: MockerFixture) -> None:
        """enrich() returns new Holding instances; originals unchanged."""
        _mock_yf_info(mocker, "AAPL", sector="Technology", quote_type="EQUITY")
        original = _make_holding("AAPL", "US")
        result = _fetcher().enrich([original])
        assert original.sector is None
        assert result[0].sector == "Technology"

    def test_all_taxonomy_sectors_covered(self) -> None:
        """Spot-check that key yFinance sector strings are mapped."""
        assert YFINANCE_SECTOR_MAP["Technology"] == "Technology"
        assert YFINANCE_SECTOR_MAP["Financial Services"] == "Financials"
        assert YFINANCE_SECTOR_MAP["Real Estate"] == "Real Estate (ex-REITs)"
        assert YFINANCE_SECTOR_MAP["Consumer Cyclical"] == "Consumer Discretionary"


# Mock helpers


def _mock_yf_info(
    mocker: MockerFixture,
    ticker: str,
    *,
    sector: str | None,
    quote_type: str,
    long_name: str = "",
) -> Any:
    ticker_mock = MagicMock()
    ticker_mock.fast_info = {"quote_type": quote_type}
    ticker_mock.info = {
        "sector": sector or "",
        "longName": long_name,
        "quoteType": quote_type,
    }
    mocker.patch(
        "src.sector.fetcher.yf.Ticker",
        side_effect=lambda t: (
            ticker_mock
            if t == ticker
            else MagicMock(fast_info={"quote_type": "EQUITY"}, info={"sector": "", "longName": ""})
        ),
    )
    return ticker_mock


def _mock_yf_etf(
    mocker: MockerFixture, ticker: str, *, top_holdings: dict[str, float] | None
) -> Any:
    ticker_mock = MagicMock()
    ticker_mock.fast_info = {"quote_type": "ETF"}
    if top_holdings is not None:
        df = pd.DataFrame(
            {"holdingPercent": list(top_holdings.values())}, index=list(top_holdings.keys())
        )
        ticker_mock.funds_data.top_holdings = df
    else:
        ticker_mock.funds_data.top_holdings = None
    mocker.patch(
        "src.sector.fetcher.yf.Ticker",
        side_effect=lambda t: (
            ticker_mock
            if t == ticker
            else MagicMock(
                fast_info={"quote_type": "EQUITY"}, funds_data=MagicMock(top_holdings=None)
            )
        ),
    )
    return ticker_mock


def _mock_sgx_api(mocker: MockerFixture, sector: str | None) -> Any:
    mock_resp = MagicMock()
    if sector is not None:
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"items": [{"category": sector}]}}
    else:
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"items": [{}]}}
    mocker.patch("src.sector.fetcher.requests.get", return_value=mock_resp)
    return mock_resp
