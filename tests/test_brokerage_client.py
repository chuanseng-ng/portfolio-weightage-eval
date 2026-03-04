"""Tests for the BrokerageClient and StubBrokerageClient classes."""

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.brokerage_client import BrokerageClient, IBKRBrokerageClient, StubBrokerageClient
from src.models import Holding


def test_stub_returns_injected_holdings(holding_us: Holding, holding_sg: Holding) -> None:
    """Test that StubBrokerageClient returns the holdings it was initialized with."""
    stub = StubBrokerageClient([holding_us, holding_sg])
    result = stub.fetch_holdings()
    assert result == [holding_us, holding_sg]


def test_stub_returns_empty_list() -> None:
    """Test that StubBrokerageClient returns an empty list when initialized with no holdings."""
    stub = StubBrokerageClient([])
    assert not stub.fetch_holdings()


def test_stub_returns_holding_instances(holding_us: Holding) -> None:
    """Test that StubBrokerageClient returns a list of Holding instances."""
    stub = StubBrokerageClient([holding_us])
    result = stub.fetch_holdings()
    assert all(isinstance(h, Holding) for h in result)


def test_stub_satisfies_protocol(holding_us: Holding) -> None:
    """Test that StubBrokerageClient can be used where BrokerageClient is expected."""
    stub = StubBrokerageClient([holding_us])
    assert isinstance(stub, BrokerageClient)


def test_ibkr_default_connection_params() -> None:
    """Test that IBKR client has default connection parameters set."""
    client = IBKRBrokerageClient()
    assert client._host == "127.0.0.1"
    assert client._port == 7497
    assert client._client_id == 1


def test_ibkr_custom_connection_params() -> None:
    """Test that IBKR client can be initialized with custom connection parameters."""
    client = IBKRBrokerageClient(host="10.5.2.10", port=4001, client_id=42)
    assert client._host == "10.5.2.10"
    assert client._port == 4001
    assert client._client_id == 42


def test_ibkr_fetch_holdings_returns_mapped_holdings() -> None:
    """Test that IBKR fetch_holdings returns a list of Holding instances with correct fields."""
    mock_contract = MagicMock()
    mock_contract.localSymbol = "AAPL"
    mock_contract.symbol = "AAPL"
    mock_contract.currency = "USD"

    mock_item = MagicMock()
    mock_item.contract = mock_contract
    mock_item.position = 10.0
    mock_item.averageCost = 150.0

    mock_ib = MagicMock()
    mock_ib.portfolio.return_value = [mock_item]

    with patch("src.ingestion.brokerage_client.IB", return_value=mock_ib):
        client = IBKRBrokerageClient()
        result = client.fetch_holdings()

    assert len(result) == 1
    assert result[0].ticker == "AAPL"
    assert result[0].market == "US"
    assert result[0].quantity == 10.0
    assert result[0].price == 150.0
    assert result[0].currency == "USD"
    mock_ib.connect.assert_called_once_with("127.0.0.1", 7497, 1)
    mock_ib.disconnect.assert_called_once()


def test_ibkr_detch_holdings_disconnects_on_error() -> None:
    """Test that IBKR fetch_holdings disconnects even if an error occurs during fetching."""
    mock_ib = MagicMock()
    mock_ib.portfolio.side_effect = RuntimeError("TWS connection lost")

    with patch("src.ingestion.brokerage_client.IB", return_value=mock_ib):
        client = IBKRBrokerageClient()
        with pytest.raises(RuntimeError, match="TWS connection lost"):
            client.fetch_holdings()

    mock_ib.connect.assert_called_once()  # finally block must always fire


def test_ibkr_falls_back_to_symbol_when_local_symbol_empty() -> None:
    """Test that IBKR fetch_holdings uses contract.symbol if localSymbol is empty."""
    mock_contract = MagicMock()
    mock_contract.localSymbol = ""  # falsy -> falls back to .symbol
    mock_contract.symbol = "D05.SI"
    mock_contract.currency = "SGD"

    mock_item = MagicMock()
    mock_item.contract = mock_contract
    mock_item.position = 100.0
    mock_item.averageCost = 32.5

    mock_ib = MagicMock()
    mock_ib.portfolio.return_value = [mock_item]

    with patch("src.ingestion.brokerage_client.IB", return_value=mock_ib):
        client = IBKRBrokerageClient()
        result = client.fetch_holdings()

    assert result[0].ticker == "D05.SI"
    assert result[0].market == "SG"
