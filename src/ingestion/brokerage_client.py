"""Brokerage API client - Protocol definition, IBKR implementation, and test stub."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ib_insync import IB

from src.exceptions import ValidationError
from src.models import Holding, detect_market


@runtime_checkable
class BrokerageClient(Protocol):
    """Protocol for fetching holdings from a brokerage account."""

    def fetch_holdings(self) -> list[Holding]:
        """Fetch holdings from the brokerage account."""
        raise NotImplementedError


class IBKRBrokerageClient:
    """Brokerage client implementation for Interactive Brokers using ib_insync."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id

    def fetch_holdings(self) -> list[Holding]:
        """Connects to IBKR, fetches portfolio holdings, and converts them to Holding instances."""
        ib = IB()  # type: ignore[no-untyped-call]
        ib.connect(self._host, self._port, self._client_id)
        try:
            portfolio_items = ib.portfolio()
            holdings: list[Holding] = []
            for item in portfolio_items:
                contract = item.contract
                ticker = contract.localSymbol or contract.symbol
                if not ticker:
                    raise ValidationError(
                        f"Missing ticker: contract {contract} has no localSymbol or symbol"
                    )
                holdings.append(
                    Holding(
                        ticker=ticker,
                        market=detect_market(ticker),
                        quantity=float(item.position),
                        price=float(item.averageCost),
                        currency=contract.currency,
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
