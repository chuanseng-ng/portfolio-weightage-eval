"""Brokerage API client - Protocol definition, IBKR implementation, and test stub."""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from ib_insync import IB

from src.exceptions import ValidationError
from src.models import VALID_CURRENCIES, Holding, detect_market


@runtime_checkable
class BrokerageClient(Protocol):
    """Protocol for fetching holdings from a brokerage account."""

    def fetch_holdings(self) -> list[Holding]:
        """Fetch holdings from the brokerage account."""
        raise NotImplementedError


class IBKRBrokerageClient:
    """Brokerage client implementation for Interactive Brokers using ib_insync."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        connect_timeout: int = 4,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._connect_timeout = connect_timeout

    def fetch_holdings(self) -> list[Holding]:
        """Connects to IBKR, fetches portfolio holdings, and converts them to Holding instances."""
        ib = IB()  # type: ignore[no-untyped-call]
        try:
            ib.connect(self._host, self._port, self._client_id, self._connect_timeout)
        except (OSError, TimeoutError) as e:
            raise ValidationError(
                f"Failed to connect to IBKR at {self._host}:{self._port}: {e}"
            ) from e
        try:
            portfolio_items = ib.portfolio()
            holdings: list[Holding] = []
            for item in portfolio_items:
                contract = item.contract
                raw_ticker = contract.localSymbol or contract.symbol
                ticker = raw_ticker.strip() if isinstance(raw_ticker, str) else ""
                if not ticker:
                    raise ValidationError(
                        f"Missing ticker: contract {contract} has no localSymbol or symbol"
                    )

                raw_currency = contract.currency
                currency = raw_currency.strip().upper() if isinstance(raw_currency, str) else ""
                if currency not in VALID_CURRENCIES:
                    raise ValidationError(
                        f"Invalid currency '{raw_currency}' for ticker '{ticker}'"
                    )

                try:
                    quantity = float(item.position)
                    if not math.isfinite(quantity):
                        raise ValueError("Quantity must be a finite number")
                except (ValueError, TypeError) as e:
                    raise ValidationError(
                        f"Invalid quantity '{item.position}' for ticker '{ticker}': {e}"
                    ) from e

                try:
                    price = float(item.averageCost)
                    if not math.isfinite(price):
                        raise ValueError("Price must be a finite number")
                except (ValueError, TypeError) as e:
                    raise ValidationError(
                        f"Invalid price '{item.averageCost}' for ticker '{ticker}': {e}"
                    ) from e

                market = detect_market(ticker)
                if market == "US" and ("." in ticker):
                    raise ValidationError(
                        f"Ticker '{ticker}' has an unrecognized suffix; "
                        "only .SI (SG) and .L (UK) are currently supported"
                    )

                holdings.append(
                    Holding(
                        ticker=ticker,
                        market=detect_market(ticker),
                        quantity=quantity,
                        price=price,
                        currency=currency,
                    )
                )
            return holdings
        finally:
            ib.disconnect()  # type: ignore[no-untyped-call]


class StubBrokerageClient:
    """Stub implementation of BrokerageClient for testing purposes."""

    def __init__(self, holdings: list[Holding]) -> None:
        self._holdings = holdings

    def fetch_holdings(self) -> list[Holding]:
        """Returns the injected list of holdings."""
        return list(self._holdings)
