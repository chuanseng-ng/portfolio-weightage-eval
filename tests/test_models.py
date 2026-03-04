"""Unit tests for the Holding model and market detection logic."""

from src.models import Holding, detect_market


def test_detect_market_us_no_suffix() -> None:
    """Tickers without suffix should default to US market."""
    assert detect_market("AAPL") == "US"


def test_detect_market_sg_si_suffix() -> None:
    """Tickers with .SI suffix should be detected as Singapore market."""
    assert detect_market("D05.SI") == "SG"


def test_detect_market_uk_l_suffix() -> None:
    """Tickers with .L suffix should be detected as UK market."""
    assert detect_market("LLOY.L") == "UK"


def test_detect_market_si_case_insensitive() -> None:
    """Tickers with .SI suffix (lowercase) should be detected as Singapore market."""
    assert detect_market("d05.si") == "SG"


def test_detect_market_l_case_insensitive() -> None:
    """Tickers with .L suffix (lowercase) should be detected as UK market."""
    assert detect_market("lloy.l") == "UK"


def test_holding_fields_stored_correctly() -> None:
    """Test that Holding dataclass stores fields correctly."""
    h = Holding(ticker="AAPL", market="US", quantity=10, price=150.0, currency="USD")
    assert h.ticker == "AAPL"
    assert h.market == "US"
    assert h.quantity == 10
    assert h.price == 150.0
    assert h.currency == "USD"


def test_holding_market_derived_from_detect() -> None:
    """Test that market can be derived from ticker using detect_market function."""
    h = Holding(
        ticker="D05.SI",
        market=detect_market("D05.SI"),
        quantity=100,
        price=32.5,
        currency="SGD",
    )
    assert h.market == "SG"
