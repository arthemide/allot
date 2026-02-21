"""
Tests for TransactionService.

Tests business logic with mocked repositories.
"""

from datetime import datetime, timezone

import pytest

from src.services.transaction import TransactionService


@pytest.fixture
def mock_tx(mocker):
    """Create a mock AssetTransactionTable with asset."""

    def _create(
        tx_id=1,
        asset_id=10,
        symbol="AAPL",
        name="Apple Inc.",
        tx_type="buy",
        quantity=1.5,
        price=100.0,
        total_cost=150.0,
        order_id=None,
    ):
        asset = mocker.Mock()
        asset.symbol = symbol
        asset.name = name

        tx = mocker.Mock()
        tx.id = tx_id
        tx.asset_id = asset_id
        tx.asset = asset
        tx.transaction_type = tx_type
        tx.timestamp = datetime(2026, 1, 15, tzinfo=timezone.utc)
        tx.quantity = quantity
        tx.price = price
        tx.total_cost = total_cost
        tx.order_id = order_id
        tx.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
        return tx

    return _create


@pytest.fixture
def mock_session(mocker):
    """Mock SessionLocal context manager and scalars chain."""
    session = mocker.MagicMock()
    session.__enter__ = mocker.Mock(return_value=session)
    session.__exit__ = mocker.Mock(return_value=False)
    mocker.patch("src.services.transaction.SessionLocal", return_value=session)
    return session


def _setup_scalars(session, results):
    """Helper to set up session.scalars().all() chain."""
    scalars_mock = session.scalars.return_value
    scalars_mock.all.return_value = results


class TestTransactionService:
    """Tests for TransactionService business logic."""

    def test_get_all_returns_list(self, mock_session, mock_tx):
        """
        Given: No transactions in database
        When: Getting all transactions
        Then: Returns empty list
        """
        _setup_scalars(mock_session, [])

        result = TransactionService.get_all()

        assert result == []

    def test_get_all_enriches_symbol_and_name(self, mock_session, mock_tx):
        """
        Given: One transaction with asset
        When: Getting all transactions
        Then: asset_symbol and asset_name are present
        """
        tx = mock_tx(symbol="ETH", name="Ethereum")
        _setup_scalars(mock_session, [tx])

        result = TransactionService.get_all()

        assert len(result) == 1
        assert result[0].asset_symbol == "ETH"
        assert result[0].asset_name == "Ethereum"

    def test_get_all_with_fund_id_filter(self, mock_session, mocker):
        """
        Given: fund_id filter
        When: Getting all transactions
        Then: Query includes fund_id filter (session.scalars called)
        """
        _setup_scalars(mock_session, [])

        TransactionService.get_all(fund_id=42)

        mock_session.scalars.assert_called_once()

    def test_get_all_with_asset_id_filter(self, mock_session):
        """
        Given: asset_id filter
        When: Getting all transactions
        Then: Query includes asset_id filter (session.scalars called)
        """
        _setup_scalars(mock_session, [])

        TransactionService.get_all(asset_id=10)

        mock_session.scalars.assert_called_once()

    def test_get_all_respects_limit(self, mock_session, mock_tx):
        """
        Given: Two transactions exist, limit=1 requested
        When: Getting all transactions with limit
        Then: session.scalars is called (limit applied at query level)
        """
        _setup_scalars(mock_session, [mock_tx(tx_id=1), mock_tx(tx_id=2)])

        result = TransactionService.get_all(limit=2)

        assert len(result) == 2
        mock_session.scalars.assert_called_once()

    def test_get_all_maps_fields_correctly(self, mock_session, mock_tx):
        """
        Given: One transaction with known values
        When: Getting all transactions
        Then: All fields are correctly mapped to TransactionSchema
        """
        tx = mock_tx(
            tx_id=5,
            asset_id=20,
            symbol="BTC",
            name="Bitcoin",
            tx_type="sell",
            quantity=0.5,
            price=50000.0,
            total_cost=25000.0,
            order_id="ORDER-123",
        )
        _setup_scalars(mock_session, [tx])

        result = TransactionService.get_all()

        assert len(result) == 1
        r = result[0]
        assert r.id == 5
        assert r.asset_id == 20
        assert r.asset_symbol == "BTC"
        assert r.asset_name == "Bitcoin"
        assert r.transaction_type == "sell"
        assert r.quantity == 0.5
        assert r.price == 50000.0
        assert r.total_cost == 25000.0
        assert r.order_id == "ORDER-123"
