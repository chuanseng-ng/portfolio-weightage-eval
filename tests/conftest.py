"""Test fixtures for the portfolio weightage evaluator."""

import io
from collections.abc import Callable

import pandas as pd
import pytest

from src.models import Holding


@pytest.fixture
def holding_us() -> Holding:
    """Fixture for a US market holding."""
    return Holding(ticker="AAPL", market="US", quantity=10, price=150.0, currency="USD")


@pytest.fixture
def holding_sg() -> Holding:
    """Fixture for a Singapore market holding."""
    return Holding(ticker="D05.SI", market="SG", quantity=100, price=32.5, currency="SGD")


@pytest.fixture
def holding_uk() -> Holding:
    """Fixture for a UK market holding."""
    return Holding(ticker="LLOY.L", market="UK", quantity=500, price=0.52, currency="GBP")


@pytest.fixture
def make_excel_bytes() -> Callable[[list[dict[str, object]]], io.BytesIO]:
    """Factory fixture that creates an in-memory Excel file from a list of dictionaries."""

    def _factory(rows: list[dict[str, object]]) -> io.BytesIO:
        buf = io.BytesIO()
        pd.DataFrame(rows).to_excel(buf, index=False)
        buf.seek(0)
        return buf

    return _factory
