"""Unit tests for the ExcelParser class."""

import io
from collections.abc import Callable

import pytest

from src.exceptions import ValidationError
from src.ingestion.excel_parser import ExcelParser
from src.models import Holding


@pytest.fixture
def parser() -> ExcelParser:
    """Fixture that returns an instance of ExcelParser."""
    return ExcelParser()


def test_parse_single_us_holding(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test parsing a single US market holding from Excel."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": 150.0, "Currency": "USD"}]
    )
    result = parser.parse(data)
    assert len(result) == 1
    assert result[0].ticker == "AAPL"
    assert result[0].market == "US"


def test_parse_multi_market_holdings(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test parsing multiple holdings from different markets in the same Excel file."""
    data = make_excel_bytes(
        [
            {"Ticker": "AAPL", "Quantity": 10, "Purchase Price": 150.0, "Currency": "USD"},
            {"Ticker": "D05.SI", "Quantity": 100, "Purchase Price": 32.5, "Currency": "SGD"},
            {"Ticker": "LLOY.L", "Quantity": 500, "Purchase Price": 0.52, "Currency": "GBP"},
        ]
    )
    result = parser.parse(data)
    assert [h.market for h in result] == ["US", "SG", "UK"]


def test_parse_empty_workbook(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test parsing an empty Excel workbook should return an empty list."""
    data = make_excel_bytes([])
    result = parser.parse(data)
    assert result == []


def test_parse_missing_ticker_column(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that missing 'Ticker' column raises ValidationError."""
    data = make_excel_bytes([{"Quantity": 10, "Purchase Price": 150.0, "Currency": "USD"}])
    with pytest.raises(ValidationError, match="ticker"):
        parser.parse(data)


def test_parse_missing_quantity_column(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that missing 'Quantity' column raises ValidationError."""
    data = make_excel_bytes([{"Ticker": "AAPL", "Purchase Price": 150.0, "Currency": "USD"}])
    with pytest.raises(ValidationError, match="quantity"):
        parser.parse(data)


def test_parse_missing_purchase_price_column(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that missing 'Purchase Price' column raises ValidationError."""
    data = make_excel_bytes([{"Ticker": "AAPL", "Quantity": 10, "Currency": "USD"}])
    with pytest.raises(ValidationError, match="purchase price"):
        parser.parse(data)


def test_parse_missing_currency_column(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that missing 'Currency' column raises ValidationError."""
    data = make_excel_bytes([{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": 150.0}])
    with pytest.raises(ValidationError, match="currency"):
        parser.parse(data)


def test_parse_zero_quantity_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that zero quantity raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 0, "Purchase Price": 150.0, "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="quantity"):
        parser.parse(data)


def test_parse_negative_price_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that negative purchase price raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": -1.0, "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="purchase price"):
        parser.parse(data)


def test_parse_invalid_currency_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that invalid currency raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": 150.0, "Currency": "XYZ"}]
    )
    with pytest.raises(ValidationError, match="currency"):
        parser.parse(data)


def test_parse_empty_ticker_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that empty ticker raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "", "Quantity": 10, "Purchase Price": 150.0, "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="ticker"):
        parser.parse(data)


def test_parse_non_numeric_quantity_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that non-numeric quantity raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": "ten", "Purchase Price": 150.0, "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="quantity"):
        parser.parse(data)


def test_parse_non_numeric_price_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that non-numeric purchase price raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": "one fifty", "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="purchase price"):
        parser.parse(data)


def test_parse_column_names_case_insensitive(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that column names are case-insensitive when parsing."""
    data = make_excel_bytes(
        [{"ticker": "AAPL", "quantity": 10, "purchase price": 150.0, "currency": "USD"}]
    )
    result = parser.parse(data)
    assert len(result) == 1
    assert isinstance(result[0], Holding)


def test_parse_from_bytesio(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that parser can read from an in-memory BytesIO Excel file."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": 150.0, "Currency": "USD"}]
    )
    assert isinstance(data, io.BytesIO)
    result = parser.parse(data)
    assert len(result) == 1
    assert isinstance(result[0], Holding)


def test_parse_nan_quantity_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that NaN quantity raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": float("nan"), "Purchase Price": 150.0, "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="quantity"):
        parser.parse(data)


def test_parse_inf_quantity_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that infinite quantity raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": float("inf"), "Purchase Price": 150.0, "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="quantity"):
        parser.parse(data)


def test_parse_nan_price_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that NaN purchase price raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": float("nan"), "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="purchase price"):
        parser.parse(data)


def test_parse_inf_price_raises(
    parser: ExcelParser, make_excel_bytes: Callable[[list[dict[str, object]]], io.BytesIO]
) -> None:
    """Test that infinite purchase price raises ValidationError."""
    data = make_excel_bytes(
        [{"Ticker": "AAPL", "Quantity": 10, "Purchase Price": float("inf"), "Currency": "USD"}]
    )
    with pytest.raises(ValidationError, match="purchase price"):
        parser.parse(data)
